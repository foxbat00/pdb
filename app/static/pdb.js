// place this before all of your code, outside of document ready.
$.fn.clicktoggle = function(a, b) {
    console.log("does this shit even run?");
    return this.each(function() {
        var clicked = false;
        $(this).bind("click", function() {
            if (clicked) {
                clicked = false;
                return b.apply(this, arguments);
            }
            clicked = true;
            return a.apply(this, arguments);
        });
    });
};

// now you can use it elsewhere in place of existing .toggle




////////////////////////  document  ready  /////////////////////


$( document ).ready(function() {

    console.log("document ready")

    function rightbar_close() {
	$('#rightbar-toggle').text("<<");
	$('#right-sidebar').animate({
	    width: "10px",
	    backgroundColor: "#000000"
	}, 400);
	$('#right-sidebar').css({ 
	    "padding-left": "0px",
	}).css({
	    "padding-right": "0px"
	})
	$('#button-sidebar').animate({
	    width: "30px",
	},400);
	$('#rightbar-toggle').text("<<");
    }


    function rightbar_open() {
	$('#right-sidebar').animate({
	    width: "50%",
	    backgroundColor: "#ffffff"
	}, 400);
	$('#right-sidebar').css({ 
	    "padding-left": "20px" 
	}).css({
	    "padding-right": "20px"
	})
	$('#button-sidebar').css({'width':'calc(50% + 20px)'});
	//$('#button-sidebar').css(
	//    'width': 'calc(50% + 20px)'
	//,400);
	$('#rightbar-toggle').text(">>");
    }
    $('#rightbar-toggle').clicktoggle(rightbar_open, rightbar_close);


    //pjax handlers
    $(document).pjax('a[pjax_main]', '#main_content');
    $(document).pjax('a[pjax_rightbar]', '#right-sidebar');
    $(document).on('submit', 'form[data-pjax]', function(event) {
      $.pjax.submit(event, '#main_content');
    });
    $('#right-sidebar').on('pjax:complete', rightbar_open);


////////////////////////  right-sidebar pjax:complete   /////////////////////

    $('#right-sidebar').on('pjax:end', rightbar_setup);

    function rightbar_setup() {

	//console.log("tags = #"+JSON.stringify(tags)+"#");

	// facets 
	$('#mytags').select2({
	    tags: tags,
	    placeholder: "Tags ...",
	    minimumInputLength: 2,
	    multiple: true,
	    tokenSeparators: [","] /*,
	    createSearchChoice:function(term, data) { 
		if ($(data).filter(function() { return this.text.localeCompare(term)===0; }).length===0) {
		    return {id:id, text:term};
		} 
	    } */
	}); 


	$('#mytags').on("change", function (e)  {
	    console.log("change "+JSON.stringify({val:e.val, added:e.added, removed:e.removed})); 
	    console.log(e.currentTarget.id);

	    if(e.added){
		console.log('added: ' + e.added.text + ' id ' + e.added.id)
		//$.post( "/view/"+e.currentTarget.id+"/tag/add", { tagAdd: e.added.text } );
		
		// figure out if tag already exists on server
		$.ajax({
		    dataType: 'json',   // causes error
		    type: 'POST',
		    url: '/json/get/Tag/'+e.added.id,
		    contentType: 'application/json; charset=utf-8',
		    success: function(response){
			console.log("response = #"+response+"#");
			var ret = response;
			//var ret = JSON.parse(response); 
			console.log("ret = #"+ret+"#");

			if (ret == {}) {
			    // tag does not exist on server
			    if(!confirm_add(e.added.text)) {
				//cancel
				return false;
			    }
			}

			//create association
			if(!alter_assoc('add','SceneTag',e.added.id, scene_id)) {
			    //failed
			    return false;
			}

		    }
		});
	    }
	    else if(e.removed){
		console.log('removed: ' + e.removed.text + ' id ' + e.removed.id)
		//$.post( "/view/"+e.currentTarget.id+"/tag/remove", { tagRemove: e.removed.text } );
		alter_assoc('delete','SceneTag',e.removed.id, scene_id);

	    }
	});







	function alter_assoc(action,linktbl,tag,scene) {
	    console.log("alter_assoc action="+action+" linktbl="+linktbl+" tag="+tag+"   scene="+scene)
	    var values = {
	    'scene_id':scene,
	    'tag_id':tag
	    };
		
	    $.ajax({
		type: 'POST',
		url: '/json/' +action+ '/' +linktbl+ '/',
		dataType: 'json',
		contentType: 'application/json; charset=utf-8',
		data: JSON.stringify(values)
	    });
	}


	function confirm_add(tag) {
	    console.log('confirm_add')
	    BootstrapDialog.show({
		message: 'Confirm adding tag: "'+tag+'"',
		buttons: [{
		label: 'Confirm new tag "'+tag+'"',
		action: add_new('tag', {'name': tag } )
		}, {
		label: 'Cancel',
		cssClass: 'btn-primary',
		action: function(dialogItself){
		    dialogItself.close();
		}
		}]
	    }); 
	}


	function add_new(thing,values) {
	    console.log("add_new t="+thing+"   values="+values)
	    $.ajax({
		type: 'POST',
		url: '/json/add/'+thing+'/',
		contentType: 'application/json; charset=utf-8',
		dataType: 'json',
		data: JSON.stringify(values)
	    }); 
	}


	// x-editable
	$.fn.editable.defaults.mode = 'inline';
	$('#display_name').editable({
	    url: '/json/update/Scene/',
	    inputClass: 'myeditable',
	    ajaxOptions: {
		type: 'POST',
		dataType: 'json',
		contentType: 'application/json; charset=utf-8'
	    },
	    validate: function(value) {
		if($.trim(value) == '') return 'This is required.';
	    },
	    params: function(params) {
	        return JSON.stringify(params);
	    },
	    success: function(response, newValue) {
	        if(!response.success) return response.msg;
	    }
	    //mode: 'inline'
	});

	$('#myrating').raty({
	    score: function() {
		return $(this).attr('data-score');
	    },
	    number: 5,
	    click: function(score, evt) {
		console.log('ID: ' + $(this).attr('id') + "  score: " + score + "  event: " + evt);
		$.ajax({
		    type: 'POST',
		    url: '/json/update/scene/',
		    contentType: 'application/json; charset=utf-8',
		    dataType: 'json',
		    data: JSON.stringify({"pk":scene_id, "rating":score})
		}); 
	    },
	    cancel: 'true',
	    cancelPlace: 'right',
	    path: '/static/bower_components/raty/lib/img/'
	});


    } // rightbar_setup

}); // document-ready close






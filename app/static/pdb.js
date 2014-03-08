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

function findWithAttr(array, attr, value) {
    for(var i = 0; i < array.length; i += 1) {
	if(array[i][attr] == value) {
	    return array[i];
	}
    }
}


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

	function format(item) {
	    return item.text;
	}

	$('#mytags').select2({
	    placeholder: 'Search',
	    allowClear: true,
	    minimumInputLength: 2,
	    multiple: true,
	    //tags: tags,
	    tokenSeparators: [','],

	    data: {
		results: tags,
		text: 'text'
	    },
	    initSelection: function (element, callback) {


		var data = [];
		$($('#mytags').val().split(",")).each(function (i) {


		    var o = findWithAttr(tags, 'id', this);

		    if (o) {
			data.push({
			    id: o.id,
			    text: o.text
			});
		    } else {
			console.log("findWithAttr returned none; likely invalid id");
		    }
		});
		console.log("data = " + JSON.stringify(data));
		callback(data);
	    },
	    createSearchChoice: function (term, data) {
		console.log("create");
		if ($(data).filter(function () {
		    return this.text.localeCompare(term) === 0;
		}).length === 0) {
		    // call $.post() to add this term to the server, receive back id
		    // return {id:id, text:term}
		    // or detect this shiftiness and do it below in the on-change

		    return {
			id: -1,
			text: term
		    };
		}
	    },

	    formatSelection: format,
	    formatResult: format
	});


	$('#mytags').on("change", function (e)  {
	    console.log("change "+JSON.stringify({val:e.val, added:e.added, removed:e.removed})); 
	    console.log(e.currentTarget.id);

	    if(e.added){
		console.log('added: ' + e.added.text + ' id ' + e.added.id)
		//$.post( "/view/"+e.currentTarget.id+"/tag/add", { tagAdd: e.added.text } );
		
		// figure out if tag already exists on server
		if (e.added.id == -1) {
		    // tag does not exist on server
		    var name = e.added.text;
		    confirm_add(name, function(id) {
			e.added.id = id; 
			if (!alter_assoc('add','SceneTag',e.added.id, scene_id)) {
			    //failed
			    return false;
			}
		    } ); 
		} else { //create association
		    if (!alter_assoc('add','SceneTag',e.added.id, scene_id)) {
			//failed
			return false;
		    }
		}
	    } else if(e.removed){
		console.log('removed: ' + e.removed.text + ' id ' + e.removed.id)
		//$.post( "/view/"+e.currentTarget.id+"/tag/remove", { tagRemove: e.removed.text } );
		alter_assoc('delete','SceneTag',e.removed.id, scene_id);

	    }
	});



	function confirm_add(tag, callback) {
	    console.log('confirm_add for tag'+tag);
	    BootstrapDialog.show({
		message: ' \
		    <p>Confirm adding tag: "'+tag+'"</p> \
		    <p>Aliases: <input type="text" id="aliases" style="width:60%" /></p> \
		    <p><small><i>Comma separated; a blank value creates no aliases</small></i></p> \
		',
		buttons: [{
		    label: 'Confirm new tag "'+tag+'"',
		    action: function(dialogItself) { 
			//var d = {"name":tag};
			console.log("tag = "+tag);
			var d = {}
			var aliases = $('#aliases').value;
			d["aliases"] = aliases;
			d["name"] = tag;
			console.log("d = "+JSON.stringify(d));
			ret = add_new('Tag', d, function (id) {
			    dialogItself.close();
			    callback(id); 
			});
		    }
		}, {
		    label: 'Cancel',
		    cssClass: 'btn-primary',
		    action: function(dialogItself){
			dialogItself.close();
		    }
		}]
	    }); 
	}


	function add_new(thing,values, callback) {
	    console.log("add_new t="+thing+"   values="+values);
	    console.log("add_new t="+thing+"   values="+JSON.stringify(values));
	    $.ajax({
		type: 'POST',
		url: '/json/add/'+thing+'/',
		contentType: 'application/json; charset=utf-8',
		dataType: 'json',
		data: JSON.stringify(values), 
		success: function(response){
		    console.log("response = #"+response+"#");
		    //var ret = JSON.parse(response); 
		    if ( response && response != {}) {
			callback(response.id);
		    }
		}

	    }); 
	}


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



	// x-editable for name
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




	// rating
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






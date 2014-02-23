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
    $('#right-sidebar').on('pjax:end', rightbar_setup);



////////////////////////  right-sidebar pjax:complete   /////////////////////


    function rightbar_setup() {
	console.log("pjax-complete being called")

	// facets with tag-it
	$('#mytags').tagit({
	    autocomplete: {
		delay: 500,
		minLength: 2,
		source: '/facetnames/tag'
	    },
	    removeConfirmation: true,
	    itemName: 'tags',
	    fieldName: 'elements',
	    // function (defined in {} ) is invoked with arguments event and ui
	    beforeTagAdded: function(event, ui) {
		// do something special
		if (!ui.duringInitialization) {
		    console.log(ui.tag);
		    // figure out if tag already exists on server
		    $.ajax({
			type: 'POST',
			url: '/get/tag/'.concat(ui.tag),
			success: function(response){
			    console.log("response = #"+response+"#");
			    var ret=JSON.parse(response); 
			    if (ret == "ERROR") {
				// tag does not exist on server
				if(!confirm_add(ui.tag)) {
				    //cancel
				    return false;
				}
				//create association
				if(!create_assoc('scene_tag',ui.tag)) {
				    //failed
				    return false;
				}
			    }
			}
		    });
		}
	    }
	});


	function create_assoc(linktbl,tag,scene) {
	    var values = {
		'scene_id':scene,
		'tag_id':tag
	    };
		    
	    $.ajax({
		type: 'POST',
		url: '/add/'+linktbl+'/',
		data: values,
		contentType: 'application/json; charset=utf-8',
		dataType: 'json'
	    });
	}

	function add_new(thing,values) {
	    $.ajax({
		type: 'POST',
		url: '/add/'+thing+'/',
		contentType: 'application/json; charset=utf-8',
		dataType: 'json',
		data: values
	    }); 
	}


	function confirm_add(tag) {
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

	// save after delay on display_name
	var timerid;
	$('#sidebar-display_name').keyup(function() {
	  var form = this;
	  clearTimeout(timerid);
	  timerid = setTimeout(function() { form.submit(); }, 2000);
	});
    }
}); // document-ready close

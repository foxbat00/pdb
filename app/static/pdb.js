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

function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}


var aliases;

////////////////////////  document  ready  /////////////////////


$( document ).ready(function() {

    console.log("document ready");

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
	});
	$('#button-sidebar').animate({
	    width: "30px",
	},400);
	$('#rightbar-toggle').text("<<");
    };


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


    // facets 

	// used for select2
	function format(item) {
	    return item.text;
	}


	function initSelection(element, callback) {

	    var data = [];
	    $($(element).val().split(",")).each(function (i) {
    
		facet = $(element).attr('id');

		console.log('this = '+this+" facet = "+facet);
		var o = 'dict not found: '+facet
		if (facet == 'mytags') {
		    o = findWithAttr(tags, 'id', this);
		} else if (facet == 'mystars') {
		    o = findWithAttr(stars, 'id', this);
		} else if (facet == 'myseries') {
		    o = findWithAttr(series, 'id', this);
		} else if (facet == 'mylabel') {
		    o = findWithAttr(labels, 'id', this);
		}
	
		console.log("initSelection");
		console.log(JSON.stringify(o));

		if (o) {
		    data.push({
			id: o.id,
			text: o.text
		    });
		} else {
		    console.log("findWithAttr returned none; likely invalid id -- "+o);
		}
	    });
	    console.log("data = " + JSON.stringify(data));;
	    callback(data);
	}



	function createSearchChoice(term, data) {
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
	}



	$('#mytags').select2({
	    placeholder: 'Tags',
	    minimumInputLength: 2,
	    multiple: true,
	    tokenSeparators: [','],
	    data: { results: tags, text: 'text' },
	    initSelection: initSelection,
	    createSearchChoice: createSearchChoice,
	    formatSelection: format,
	    formatResult: format
	});

	$('#mystars').select2({
	    placeholder: 'Stars',
	    minimumInputLength: 2,
	    multiple: true,
	    tokenSeparators: [','],
	    data: { results: stars, text: 'text' },
	    initSelection: initSelection,
	    createSearchChoice: createSearchChoice,
	    formatSelection: format,
	    formatResult: format
	});


	$('#myseries').select2({
	    minimumInputLength: 2,
	    multiple: true,
	    maximumSelectionSize: 1,
	    tokenSeparators: [','],
	    data: { results: series, text: 'text' },
	    initSelection: initSelection,
	    createSearchChoice: createSearchChoice,
	    formatSelection: format,
	    formatResult: format
	});


	$('#mylabel').select2({
	    minimumInputLength: 2,
	    //multiple: false,
	    multiple: true,
	    maximumSelectionSize: 1,
	    tokenSeparators: [','],
	    data: { results: labels, text: 'text' },
	    initSelection: initSelection,
	    createSearchChoice: createSearchChoice,
	    formatSelection: format,
	    formatResult: format
	});



	$('#mytags,#mystars,#myseries,#mylabel').each( function () {
	    $(this).on("change", function (e)  {
		console.log("change "+JSON.stringify({val:e.val, added:e.added, removed:e.removed})); 
		console.log('current target id = '+e.currentTarget.id);
		// TODO FIXME 
		var x = e.currentTarget.id.replace(/^my/,'');
		var y;
		if (x != 'series') { x.replace(/s$/,'');}
		var target = capitalize(y);
		//var target = e.currentTarget.id.replace('^my(.*)s$', function(v) { return v.capitalize(); });
		console.log('target = '+target);

		if(e.added){
		    console.log('added: ' + e.added.text + ' id ' + e.added.id)
		    
		    // figure out if tag already exists on server
		    if (e.added.id == -1) {
			// tag does not exist on server
			var name = e.added.text;
			confirm_add(target, name, function(id) {
			    if (id != -1) {
				e.added.id = id; 
				if (!alter_assoc('add',target,e.added.id, scene_id)) {
				    //failed
				    return false;
				}
			    } else { 
				return false; 
			    }
			} ); 
		    } else { //create association
			if (!alter_assoc('add',target,e.added.id, scene_id)) {
			    //failed
			    return false;
			}
		    }
		} else if(e.removed){
		    console.log('removed: ' + e.removed.text + ' id ' + e.removed.id)
		    alter_assoc('delete',target,e.removed.id, scene_id);

		}
	    });
	});



	function confirm_add(facet, name, callback) {
	    console.log('confirm_add for '+facet+'  '+name);
	    BootstrapDialog.show({
		message: ' \
		    <p>Confirm adding '+facet+': "'+name+'"</p> \
		    <p>Aliases: <input type="text" id="myaliases" style="width:60%" /></p> \
		    <p><small><i>Comma separated; a blank value creates no aliases</small></i></p> \
		    <script>$("#myaliases").bind("change, paste, keyup",  \
			function () { aliases = $(this).val();  }); \
		    </script> \
		',
		buttons: [{
		    label: 'Confirm new '+facet+': "'+name+'"',
		    action: function(dialogItself) { 
			//var d = {"name":tag};
			console.log(facet+" = "+name);
			var d = {};
			var a = aliases;
			console.log("a = "+a);
			//var aliases = $('#aliases').value;
			d["aliases"] = a;
			d["name"] = name;
			console.log("d = "+JSON.stringify(d));
			ret = add_new(facet, d, function (id) {
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


	function alter_assoc(action,facet,id,scene) {
	    console.log("alter_assoc action="+action+" facet="+facet+" id="+id+"   scene="+scene);
	    var values = {};
	    field = facet.toLowerCase()+'_id';
	    values[field] = id ;
	    if (facet == 'Tag' || facet == 'Star') {
		linktbl = 'Scene'+facet;
		values['scene_id'] = scene;
		    
		$.ajax({
		    type: 'POST',
		    url: '/json/' +action+ '/' +linktbl+ '/',
		    dataType: 'json',
		    contentType: 'application/json; charset=utf-8',
		    data: JSON.stringify(values)
		});
	    } else {
		values['pk'] = scene;
		$.ajax({
		    type: 'POST',
		    url: '/json/update/scene/',
		    dataType: 'json',
		    contentType: 'application/json; charset=utf-8',
		    data: JSON.stringify(values)
		});

	    }
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


	// x-editable for series number
	$('#series_number').editable({
	    url: '/json/update/Scene/',
	    inputClass: 'myeditable',
	    ajaxOptions: {
		type: 'POST',
		dataType: 'json',
		contentType: 'application/json; charset=utf-8'
	    },
	    validate: function(value) {
		if($.trim(value) == '') { return 'This is required.'; }
		else if(!isNaN(value)) { return 'Numbers only'; }
	    },
	    params: function(params) {
	        return JSON.stringify(params);
	    },
	    success: function(response, newValue) {
	        if(!response.success) return response.msg;
	    }
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






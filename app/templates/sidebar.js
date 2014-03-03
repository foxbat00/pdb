

////////////////////////  document  ready  /////////////////////


$(document ).ready(function() {

    console.log("sidebar document ready");


	// facets 
	$('#mytags').select2({
	    tags: tags,
	    placeholder: "Tags ...",
	    minimumInputLength: 2,
	    multiple: true,
	    tokenSeparators: [","]
	    //allowClear: true 
	});


}); // document-ready close




/*	$('#mytags').on("change", function (e)  {
	    console.log("change "+JSON.stringify({val:e.val, added:e.added, removed:e.removed})); 
	    console.log(e.currentTarget.id);

	    if(e.added){
		$.post( "/view/"+scene_id+"/tag/add", { tagAdd: e.added.text } );
	    }
	    else if(e.removed){
		$.post( "/view/"+scene_id+"/tag/remove", { tagRemove: e.removed.text } );
	    }
	});
	*/

/* ,
	    createSearchChoice: function(term, data) {
		if ($(data).filter(function() {
		    return this.name.localeCompare(term) === 0;
		}).length === 0) {
		    return {id: 0, name: term};
		}

	    },
	    ajax: {
		url: '/facet/tag',
		quietMillis: 500,
		dataType: 'json',
		type: 'GET',
		data: function (term, page) {
		    return {
			searchq: term, // search term
		    };
		},
		results: function(data, page) {
		    return {results: data};
		}
	    },
	    formatSelection: function(data) {
		return data.name
	    },
	    formatResult: function(data) {
		return data.name
	    },
	    initSelection: function(element, callback) {
		$(element.val().split(",")).each(function(i) {
                    data.push({
                        id: i,
                        title: data[i].text
                    });
                });
		callback(data);
	    }
	    */

//	}); // close select2




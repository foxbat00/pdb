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
    //$('#right-sidebar').on('pjax:end', rightbar_setup);
    // this is in sidebar.js




}); // document-ready close

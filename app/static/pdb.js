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


$( document ).ready(function() {

    function rightbar_close() {
	$('#rightbar-toggle').text("<<");
	$('#right-sidebar').animate({
	    width: "10px",
	    backgroundColor: "#000000"
	}, 400);
	$('#button-sidebar').animate({
	    width: "30px",
	},400);
	$('#rightbar-toggle').text("<<");
    }
    function rightbar_open() {
	$('#right-sidebar').animate({
	    width: "200px",
	    backgroundColor: "#ffffff"
	}, 400);
	$('#button-sidebar').animate({
	    width: "220px",
	},400);
	$('#rightbar-toggle').text(">>");
    }
    $('#rightbar-toggle').clicktoggle(rightbar_open, rightbar_close);


});


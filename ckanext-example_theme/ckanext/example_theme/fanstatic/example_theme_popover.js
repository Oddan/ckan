"use strict";

ckan.module('example_theme_popover', function ($) {
    return {
	initialize: function () {
	    var num_resources = this.options.num_resources;
	    var license = this.options.license;
	    var content = 'NUM resources, LICENSE'
		.replace('NUM', this.options.num_resources)
	        .replace('LICENSE', this.options.license)

	    this.el.popover({title: this.options.title,
			     content: content,
			     placement: 'left'});
	    
	    console.log("I've been initialized again for element: ", this.el);
	}
    };
});

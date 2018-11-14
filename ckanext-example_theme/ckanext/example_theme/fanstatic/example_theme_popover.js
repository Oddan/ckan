"use strict";

ckan.module('example_theme_popover', function ($) {
    return {
	initialize: function () {

	    $.proxyAll(this, /_on/);

	    // this.el.popover({title: this.options.title, html: true,
	    // 		     content: this._('Loading...'), placement: 'left'});

	    this.el.on('click', this._onClick);
	    this.sandbox.subscribe('dataset_popover_clicked',
					  this._onPopoverClicked);
	},

	teardown: function() {
	    this.sandbox.unsubscribe('dataset_popover_clicked',
				     this._onPopoverClicked());
	},
	
	_snippedReceived: false,
	
	_onClick: function(event) {
	    if (!this._snippedReceived) {
		this.sandbox.client.getTemplate('example_theme_popover.html',
						this.options,
						this._onReceiveSnippet,
						this._onReceiveSnippetError);
		this._snippedReceived = true;
	    }
	    this.sandbox.publish('dataset_popover_clicked', this.el);
	},

	_onPopoverClicked: function(button) {
	    if (button != this.el) {
		this.el.popover('hide');
	    }
	},
	
	_onReceiveSnippet: function(html) {
	    this.el.popover('destroy');

	    this.el.popover({title: this.options.title, html: true,
	    		     content: html, placement: 'left'});

	    this.el.popover('show');
	},

	_onReceiveSnippetError: function(error) {
	    this.el.popover('destroy');

	    var content = error.status + ' ' + error.statusText + ' :(';
	    this.el.popover({title: this.options.title, html: true,
			     content: content, placement: 'left'});
	    this.el.popover('show');
	    this_.snippetReceived = true;
	}
    };
});

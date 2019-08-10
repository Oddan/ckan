"use strict";


function multiselect_synclist(selectname, listname) {

    var selector = document.getElementById(selectname);
    var selected = Array.prototype.filter.apply(
        selector.options, [ function(o) { return o.selected;}]);
    var synclist = document.getElementById(listname);

    // clear list
    while (synclist.firstChild) {
        synclist.removeChild(synclist.firstChild);
    }
    
    var item, content;
    for (var i = 0; i < selected.length; i++) {
        item = document.createElement('li');
        content = document.createTextNode(selected[i].text);
        item.appendChild(content);
        synclist.appendChild(item);
    }
}

"use strict";


function set_enum_input_visibility() {
    var dtype = document.getElementById('field-datatype').value;
    var target = document.getElementById('enum-input');
    if (dtype == 'ENUM')
        target.style.display='block';
    else 
        target.style.display='none';
}

function activate_relevant_items(item_class_name, getid_fun, show_fun, hide_fun)
{
    var ca = document.getElementsByClassName(item_class_name);
    var category = document.getElementById('field-category').value
    for (var i = 0; i < ca.length; i++) 
        if (equal_or_super(getid_fun(ca[i]), category)) 
            show_fun(ca[i]);
        else 
            hide_fun(ca[i]);
}

//ca[i].style.display='none';
//ca[i].style.display='block';

function class_id_to_intlist(cls_id) {
    return cls_id.split('.').map(function(x) {return parseInt(x, 10);});
}

function equal_or_super(item, reference) {
    // return 'true' if the tested item is equal to, or a superclass of, the
    // reference
    var ilist = class_id_to_intlist(item);
    var rlist = class_id_to_intlist(reference);

    for (var i = 0; i != 3; ++i)
        if (ilist[i] != 0 && ilist[i] != rlist[i])
            return false
    return true
}


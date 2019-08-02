function init_edit_category_metadata() {
    if (document.getElementById('field-category')) {
        // if this element exist, it means that the form is activated, and we
        // must initialize it.
        set_enum_input_visibility();
        activate_relevant_tables();
    }
}

function activate_relevant_tables() {
    activate_relevant_items('cat_atts',
                            function (x) {return x.id}, // get id
                            function (x) {x.style.display='block';}, // show fun
                            function (x) {x.style.display='none'; }  // hide fun
                           );
}

window.onload = init_edit_category_metadata

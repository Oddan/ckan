function init_edit_resource_metadata() {
    activate_relevant_input()
}

function activate_relevant_input() {
    activate_relevant_items(
        'category-metadata',
        function (x) { return x.
                       getElementsByClassName('form-control')[0].
                       getAttribute('code')}, // get id
        function (x) { x.style.display='block';
                       x.getElementsByClassName('form-control')[0].
                       removeAttribute('disabled');
                     }, // show fun
        function (x) { x.style.display='none';
                       x.getElementsByClassName('form-control')[0].
                       setAttribute('disabled', 'true');
                     }, // hide fun
    );
}

window.onload = init_edit_resource_metadata

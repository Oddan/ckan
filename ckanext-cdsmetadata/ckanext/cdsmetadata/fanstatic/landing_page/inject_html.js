"use strict"

ckan.module('inject_html', function ($) {
    return {
        initialize: function() {
            var custom_html = this.options.custom_html;
            var xhttp;
            var elem = this.el[0];

            xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function () {
                if (this.readyState == 4) {
                    if (this.status == 200) { elem.innerHTML = this.responseText;}
                    if (this.status == 404) {
                        elem.innerHTML =
                            "<h2>This dataset does not have a dedicated landing page yet.</h2>"
                    }
                }
            };
            xhttp.open("GET", custom_html, true);
            xhttp.send();
            return;
        }
    }
});
           
// ======================= Form-specific, free functions =======================

// This script gets called when the form to download resources is submitted.
// It checks that at least one resource has been selected before submitting the
// request, and raises a warning otherwise.

function validate_form() {
    var checkboxes = document.querySelectorAll('input[id="resource"]')
    //var checkedOne = Array.prototype.slice.call(checkboxes).some(x => x.checked)
    var checkedOne = Array.prototype.slice.call(checkboxes).some(function (x) {return x.checked;})
    if (checkedOne){
        return true
    }
    else {
        alert("Please select at least one resource to download.")
        return false
    }
}

function select_all_resources(elem) {
    var i
    var checkboxes = document.querySelectorAll('input[id="resource"]')
    for (i = 0; i != checkboxes.length; i++){
        if (!checkboxes[i].hasAttribute('disabled')) {
            checkboxes[i].checked = true;
        }
    }
    elem.setAttribute("onclick", "deselect_all_resources(this)")
    elem.value="Deselect all";
}

function deselect_all_resources(elem) {
    var i
    var checkboxes = document.querySelectorAll('input[id="resource"]')
    for (i = 0; i != checkboxes.length; i++) {
        checkboxes[i].checked = false;
    }
    elem.setAttribute("onclick", "select_all_resources(this)")
    elem.value="Select all";
}


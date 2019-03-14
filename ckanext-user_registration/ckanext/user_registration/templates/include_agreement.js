
function includeHTML() {
  var z, i, elem, file, xhttp;
  /* loop through a collection of HTML elements */
  z = document.getElementsByTagName("*");
  for (i=0; i<z.length; i++) {
    elem = z[i];
    /* search for elements with a certain attribute */
    file = elem.getAttribute("include-agreement");
    if (file) {
      /* make HTTP request using the attribute as the file name */
      xhttp = new XMLHttpRequest();
      xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
          if (this.status == 200) {elem.innerHTML = this.responseText;}
          if (this.status == 404) {elem.innerHTML = "This agreement is missing or lost. Please contact the administrator."}
          /* remove the attribute and call the function once more */
          elem.removeAttribute("include-agreement");
          includeHTML();
        }
      }
      xhttp.open("GET", file, true);
      xhttp.send();
      /*exit function */
      return;
    }
  }
  
};


  function includeHTML() {
    var z, i, elem, file, xhttp;
    /* loop through a collection of HTML elements */
    z = document.getElementsByTagName("*");
    for (i=0; i<z.length; i++) {
      elem = z[i];
      /* search for elements with a certain attribute */
      file = elem.getAttribute("custom-include-html");
      if (file) {
        /* make HTTP request using the attribute as the file name */
        xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
          if (this.readyState == 4) {
            if (this.status == 200) {elem.innerHTML = this.responseText;}
            if (this.status == 400) {elem.innerHTML = "Page not found."}
            /* remove the attribute and call the function once more */
            elem.removeAttribute("custom-include-html");
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

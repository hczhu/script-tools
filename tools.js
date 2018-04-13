function extractText(root) {
  if (root.children.length === 0 && root.textContent !== null && root.textContent !== '') {
   return root.textContent;
  }
  var res = '';
  for (var i = 0; i < root.children.length; ++i) {
    var sub = extractText(root.children[i]);
    if (sub !== '') {
      if (res !== '') res += ' ';
      res += sub;
    }
  }
  return res;
}
// example:
// traverseXpath("//a[@class='item-field item-symbol']", 
//         function(itr) {console.log(extractText(itr));})
function traverseXpath(xpath, cb) {
  var nodes = document.evaluate(xpath, document, null, XPathResult.ANY_TYPE, null);
  var itr = nodes.iterateNext();
  while (itr){
    cb(itr);
    itr = nodes.iterateNext();
  }
}


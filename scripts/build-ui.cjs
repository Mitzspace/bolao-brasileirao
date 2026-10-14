const fs = require('fs');
fs.mkdirSync('static/js', {recursive:true});
fs.copyFileSync('node_modules/alpinejs/dist/cdn.min.js', 'static/js/alpine.min.js');

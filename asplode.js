var sys = require('sys'),
    http = require('http'),
    crypto = require('crypto'),  
    url = require("url"),
    path = require("path"),  
    fs = require("fs"),
    io = require('socket.io'),
    json = JSON.stringify,
    log = sys.puts;

var server = http.createServer(function(request, response) {
  var uri = url.parse(request.url).pathname;  
  var filename = path.join(process.cwd(), uri);
  log("Filename: "+ filename);
  path.exists(filename, function(exists) {  
    if(!exists) {  
      response.sendHeader(404, {"Content-Type": "text/plain"});  
      response.write("404 Not Found\n");  
      response.close();  
      return;  
    }  

    fs.readFile(filename, "binary", function(err, file) {  
      if(err) {  
        response.sendHeader(500, {"Content-Type": "text/plain"});  
        response.write(err + "\n");  
        response.close();  
        return;  
      }  

      response.sendHeader(200);  
      response.write(file, "binary");  
      response.close();  
    });  
  });
});

var socket = io.listen(server);

server.listen(8000);

socket.on('connection', function(client) {
  client.on('message', function(message) {
    log("Received: "+ message);
    try {
      request = JSON.parse(message.replace('<', '&lt;').replace('>', '&gt;'));
    } catch (SyntaxError) {
      log('Invalid JSON:');
      log(message);
      return false;
    }

    if(request.action != 'close' && request.action != 'move' && request.action != 'speak') {
      log('Ivalid request:' + "\n" + message);
      return false;
    }

    if(request.action == 'speak') {
      request.email = crypto.createHash('md5').update(request.email).digest("hex");
      client.send(json(request));
    }
    
    request.id = client.sessionId
    client.broadcast(json(request));
  });

  client.on('disconnect', function(){
    client.broadcast(json({'id': client.sessionId, 'action': 'close'}));
  });
});


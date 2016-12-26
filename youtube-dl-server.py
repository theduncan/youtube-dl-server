import json
import os
import subprocess
from queue import Queue
from bottle import route, run, Bottle, request, static_file
from threading import Thread

app = Bottle()

@app.route('/yt')
def dl_queue_list():
    return static_file('index.html', root='./')

@app.route('/yt/static/:filename#.*#')
def server_static(filename):
    return static_file(filename, root='./static')

@app.route('/yt/q', method='GET')
def q_size():
    return { "success" : True, "size" : json.dumps(list(dl_q.queue)) }

@app.route('/yt/q', method='POST')
def q_put():
    url = request.forms.get( "url" )
	
    if ( request.forms.get( "media" ) != "" ):
        media = request.forms.get( "media" )
    else:
        media = "video"
		
    if "" != url:
        dl_q.put( url, media )
        print("Added url " + url + " to the download queue")
        return { "success" : True, "url" : url }
    else:
        return { "success" : False, "error" : "yt called without a url" }

def dl_worker():
    while not done:
        item = dl_q.get()
        download(item.url, item.media)
        dl_q.task_done()

def download(url, media):
    print("Starting " + media + " download of " + url)
    if (media == "audio" ) :
        command = ['/usr/local/bin/youtube-dl', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', '-x', '--audio-format=mp3', '--audio-quality=0', url]
    else:
        command = ['/usr/local/bin/youtube-dl', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', url]
		
    subprocess.call(command, shell=False)
    print("Finished " + media + " downloading " + url)

dl_q = Queue();
done = False;
dl_thread = Thread(target=dl_worker)
dl_thread.start()

print("Started download thread")

app.run(host='0.0.0.0', port=9191, debug=True)
done = True
dl_thread.join()

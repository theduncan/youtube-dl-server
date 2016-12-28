import json
import os
import subprocess
import uuid
from array import array
from json import dumps
from pystalkd.Beanstalkd import Connection
from queue import Queue
from bottle import route, run, Bottle, request, static_file
from threading import Thread

class Job(object):
    def __init__(self, url, media):
        self.url = url
        self.media = media
        self.msg = '1'
        self.progress = 'new'
        self.ID = uuid.uuid1()
        print ('New '+ media +' download: ', url)
        return
        
    def SetProgress(self, progress):
        self.progress = progress
        
    def GetProgress (self):
        return self.progress
    
    def GetJobStatus_MSG (self):
        rtn = [{ "ID" : str(self.ID), "URL" : self.url, "Media" : self.media,  "Progress" : self.progress}]
        return rtn



beanstalk = Connection("172.17.0.5", 11300) 
beanstalk.use('MSG')

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
        CurJob = Job(url, media)
        dl_q.put( CurJob )
        print("URL: "+ CurJob.url ) 
        beanstalk.put(dumps(Job.GetJobStatus_MSG()))
        rtn = [{ "Job_ID" : CurJob.ID, "Media" : CurJob.media, "Return_Message" : CurJob.msg, "Progress" : CurJob.progress }]
    else:
        rtn =  [{ "Job_ID" : "Failed", "error" : "URL error" }]
    return ( dumps(rtn) )

def dl_worker():
    while not done:
        item = dl_q.get()
        download(item)
        dl_q.task_done()

def download(item):
    item.SetProgress('Starting')
    print("Starting " + item.media + " download of " + item.url)
    if ( item.msg == '1' ) :
        beanstalk.put(dumps(item.GetJobStatus_MSG()))
    if (item.media == "audio" ) :
        command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', '-x', '--audio-format=mp3', '--audio-quality=0', item.url]
    else:
        command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', item.url]
		
    subprocess.call(command, shell=False)
    item.SetProgress('Finished')
    if ( item.msg == '1' ) :
        beanstalk.put(dumps(item.GetJobStatus_MSG()))
    print("Finished " + item.media + " downloading " + item.url)

dl_q = Queue();
done = False;
dl_thread = Thread(target=dl_worker)
dl_thread.start()

print("Started download thread")

app.run(host='0.0.0.0', port=9191, debug=True)
done = True
dl_thread.join()

import json
import os
import subprocess
import uuid
import redis
from array import array
from json import dumps
from queue import Queue
from bottle import route, run, Bottle, request, static_file
from threading import Thread

class Job(object):
    def __init__(self, url, media):
        self.url = url
        self.media = media
        self.msg = True
        self.progress = 'new'
        self.ID = uuid.uuid1()
        print ('New '+ media +' download: ', url)
        return
        
    def SetProgress(self, progress):
        self.progress = progress
        
    def GetProgress (self):
        return self.progress
        
    def SetPlaylist (self, playlist):
        self.Playlist = playlist
        
    def GetPlaylist (self):
        return self.Playlist
    def SetPath(self, path):
        self.Path = path
        
    def GetJobStatus_MSG (self, header='YT: Job'):
        rtn = [ header, { "ID" : str(self.ID), "URL" : self.url, "Media" : str(self.media),  "Progress" : self.progress, "Playlist" : self.Playlist}]
        return rtn


class RedisQueue(object):
    """Simple Queue with Redis Backend"""
    def __init__(self, name, namespace='queue', **redis_kwargs):
        """The default connection parameters are: host='localhost', port=6379, db=0"""
        self.__db= redis.Redis(host='172.17.0.7', **redis_kwargs) 
        """ Need to work out how to correctly link redis, so that host can go back to localhost, and not hardwired."""
        self.key = '%s:%s' %(namespace, name)

    def qsize(self):
        """Return the approximate size of the queue."""
        return self.__db.llen(self.key)

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        return self.qsize() == 0

    def put(self, item):
        """Put item into the queue."""
        self.__db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue. 

        If optional args block is true and timeout is None (the default), block
        if necessary until an item is available."""
        if block:
            item = self.__db.blpop(self.key, timeout=timeout)
        else:
            item = self.__db.lpop(self.key)

        if item:
            item = item[1]
        return item

    def get_nowait(self):
        """Equivalent to get(False)."""
        return self.get(False)





msg_q = RedisQueue('Msg_Return')
log_q = RedisQueue('YT_Log')
msg_q.put('YT: Starting')

app = Bottle()
log = True

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
        q.put(json.dumps(CurJob.GetJobStatus_MSG()))
        rtn = ["return", { "Job_ID" : str(CurJob.ID), "Media" : CurJob.media, "Return_Message" : CurJob.msg, "Progress" : CurJob.progress }]
    else:
        rtn =  ["return", { "Job_ID" : "Failed", "error" : "URL error" }]
    return ( dumps(rtn) )

def dl_worker():
    while not done:
        item = dl_q.get()
        download(item)
        dl_q.task_done()

        
def dl_Playlist_Check(url):
    command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '--skip-download', '--flat-playlist', item.url]
    subprocess.call(command, shell=False, stdout=Output)
    for line in Output:
        if ( 'Downloading playlist' in line ):
            return True
    return False
                
        
def download(item):
    item.SetProgress('Starting')
    item.SetPlaylist(dl_Playlist_Check(item.url))
    if ( log ):
        log_q.put(dumps(item.GetJobStatus_MSG()))
    if ( item.GetPlaylist() == False ):
        if (item.media == "audio" ):
            command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', '-x', '--audio-format=mp3', '--audio-quality=0', item.url]
        else:
            command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(title)s.%(ext)s', item.url]
    elif ( item.GetPlaylist() == True ):
        if (item.media == "audio" ):
            command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(playlist)s/%(playlist_index)s_-_%(title)s.%(ext)s', '-x', '--audio-format=mp3', '--audio-quality=0', item.url]
        else:
            command = ['/usr/local/bin/youtube-dl', '-4', '--restrict-filenames', '-o', '/dl/%(playlist)s/%(playlist_index)s_-_%(title)s.%(ext)s', item.url]
    subprocess.call(command, shell=False)
    item.SetProgress('Finished')
    if ( log ) :
        log_q.put(str(dumps(item.GetJobStatus_MSG())))
        print("Finished " + item.media + " downloading " + item.url)
        
    if ( item.msg ):
        msg_q.put(str(dumps(item.GetJobStatus_MSG())))  
        """ Need nicer way to pass job completion, need to get filepath out of youtube-dl"""
    

dl_q = Queue();
done = False;
dl_thread = Thread(target=dl_worker)
dl_thread.start()

log.put("YT: Started download thread")

app.run(host='0.0.0.0', port=9191, debug=True)
done = True
dl_thread.join()

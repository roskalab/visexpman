import subprocess,numpy,os
from visexpman.engine.generic import gui
def video_splitter():
    filename=gui.file_input('Select video file', root=os.path.expanduser('~'))
    chunk_duration=gui.text_input('Chunk duration in minutes', default='10')
    try:
        chunk_duration=float(chunk_duration)
    except:
        gui.message('Error', 'Invalid duration: {0}'.format(chunk_duration))
        return
    try:
        print(' '.join(['ffmpeg','-i', '{0}'.format(filename), '-vcodec', 'copy', '-an', '-f', 'null', '-']))
        p=subprocess.Popen(['ffmpeg','-i', '{0}'.format(filename), '-vcodec', 'copy', '-an', '-f', 'null', '-'],stderr=subprocess.PIPE)
        res=p.stderr.read().decode('utf-8')
        durstr=res.split('Duration: ')[1].split(', ')[0]
        overall_duration=(numpy.array(list(map(float, durstr.split(':'))))*numpy.array([3600,60,1])).sum()
        chunk_duration*=60
        nchunks=int(numpy.ceil(overall_duration/chunk_duration))
        for i in range(nchunks):
            outputfn='{0}_{1:0=2}{2}'.format(os.path.splitext(filename)[0],i,os.path.splitext(filename)[1])
            subprocess.call('ffmpeg -i "{0}" -ss {1} -t {2} -c copy "{3}"'.format(filename, i*chunk_duration, chunk_duration, outputfn),shell=True)
        gui.message('Info', 'Done')
    except:
        import traceback
        print(traceback.format_exc())
        import pdb
        pdb.set_trace()

if __name__ == "__main__":
    video_splitter()
    

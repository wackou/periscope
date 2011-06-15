# -*- coding: utf-8 -*-

#   This file is part of periscope.
#
#    periscope is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    periscope is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with periscope; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import threading
import plugins
import logging
import traceback

class PluginWorker(threading.Thread):
    ''' Threaded plugin worker '''
    def __init__(self, taskQueue, resultQueue):
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue
        self.logger = logging.getLogger('periscope.worker')

    def run(self):
        while True:
            task = self.taskQueue.get()
            result = None
            try:
                if not task: # this is a poison pill
                    break
                elif task['task'] == 'list': # the task is a listing
                    # get the corresponding plugin
                    plugin = getattr(plugins, task['plugin'])(task['config'])
                    # split tasks if the plugin can't handle multi-thing queries
                    splitedTasks = plugin.splitTask(task)
                    myTask = splitedTasks.pop()
                    for st in splitedTasks:
                        self.taskQueue.put(st)
                    result = plugin.list(myTask['filenames'], myTask['languages'])
                elif task['task'] == 'download': # the task is to download
                    result = None
                    while task['subtitle']:
                        subtitle = task['subtitle'].pop(0) 
                        # get the corresponding plugin
                        plugin = getattr(plugins, subtitle["plugin"])(task['config'])
                        path = plugin.download(subtitle)
                        if path:
                            subtitle["subtitlepath"] = path
                            result = subtitle
                            break
                else:
                    self.logger.error('Unknown task %s submited to worker %s' % (task['task'], self.name))
            except:
                self.logger.debug(traceback.print_exc())
                self.logger.error("Worker couldn't do the job %s, continue anyway" % task['task'])
            finally:
                self.resultQueue.put(result)
                self.taskQueue.task_done()
        self.logger.debug("Thread %s terminated" % self.name)

#!/usr/bin/python

import os
import random
import gobject
import gtk
import threading
import Queue
import time

NUM_THREADS = 3

# Inicializo threads con gtk
gtk.gdk.threads_init()

class MainApp:

    def __init__(self):
        self._builder = gtk.Builder()
        self._builder.add_from_file(os.path.join("ui", "main.ui"))
        self._builder.connect_signals(self)
        
        self.main_window = self._builder.get_object("main_window")
        self.main_window.show_all()
        
        self.downloads_store = self._builder.get_object("downloads_store")
        self.downloads_treeview = self._builder.get_object("downloads_treeview")
        
        self._max_threads = 2
        self._exit = False
        self._threads = []
        
        self.queue = Queue.Queue()
        self.queue_manager()
        
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()
    
    def progress_handler(self, progress, download_id):
        if progress == 100:
            progress_text = "Descarga terminada"
        elif progress == -1:
            progress_text = "Descarga cancelada"
            progress = 0
        else:
            progress_text = "Descargando..."
            
        # Update the progress bar in the treeview
        for row in self.downloads_store:
            if row[3] == download_id:
                row[2] = progress
                row[1] = progress_text
                break
    
    def add_url(self, url):
        url = url.replace("\n", "")
        # Get an ID for this thread
        download_id = random.randint(1, 1000000)
        #self._threads[download_id] = url
        self.downloads_store.append([url, "En cola..", 0, download_id])
        self.queue.put((url, download_id))

    def queue_manager(self):
        #max_threads = int(self._builder.get_object("max_threads_spin").get_value())
        max_threads = NUM_THREADS
        
        # Spawn a pool of threads, and pass them queue instance 
        for i in range(max_threads):
            t = ThreadUrlGrabber(self.queue, self.progress_handler)
            self._threads.append(t)
            t.start()
            
        
    """
    Event Handlers methods
    """
        
    def on_main_window_delete_event(self, widget, event):
        # Stop current threads
        main_thread = threading.currentThread()
        
        for th in threading.enumerate():
            # Si es el thread principal lo salteamos para evitar deadlock
            if th is main_thread:
                continue
            th.stop()
            
        gtk.main_quit()
        
    def on_stop_button_clicked(self, widget):
        (model, row_iter) =  self.downloads_treeview.get_selection().get_selected()
        download_id =  self.downloads_store.get_value(row_iter, 3)
        # Find the thread downloading this item and stop it
        for t in self._threads:
            if t.download_id == download_id:
                t.stop()
                break
        
    def on_start_button_clicked(self, widget):
        pass
        
    def on_remove_url_button_clicked(self, widget):
        (model, row_iter) =  self.downloads_treeview.get_selection().get_selected()
        progress =  self.downloads_store.get_value(row_iter, 2)
        if progress in [0, -1, 100]:
            self.downloads_store.remove(row_iter)
    
    def on_add_url_button_clicked(self, widget):
        try:
            builder = gtk.Builder()
            builder.add_from_file(os.path.join("ui", "main.ui"))
            input_diag = builder.get_object("input_dialog")
            ret = input_diag.run()
            if ret == gtk.RESPONSE_ACCEPT:
                url = builder.get_object("url_entry").get_text()
                self.add_url(url)
                
        finally:
            input_diag.destroy()
            
    def on_max_threads_spin_value_changed(self, widget):
        pass
            

class ThreadUrlGrabber(threading.Thread):
    
    """ Threaded Url """
    
    def __init__(self, queue, pg_callback):
        threading.Thread.__init__(self)
        self.download_id = None
        self.queue = queue
        self.progress_callback = pg_callback
        self._stop_event = threading.Event()
    
    def notify_progress(self, progress):
        gtk.threads_enter()
        self.progress_callback(progress, self.download_id)
        while gtk.events_pending():
            gtk.main_iteration()
        gtk.threads_leave()
    
    def run(self):
        while not self._stop_event.isSet():
            time.sleep(0.2)             
            try:
                # Tomar una url de la cola
                url, download_id = self.queue.get(False)
                self.download_id = download_id
                
                # Simulo una descarga...
                for i in range(1, 101):
                    if self._stop_event.isSet():
                        self.notify_progress(-1)
                        break;
                    self.notify_progress(i)
                    time.sleep(random.uniform(0, 1))
                
                # notificar a la cola que el trabajo termino
                self.queue.task_done()
            except Queue.Empty:
                continue
    
    def stop(self):
		"""Stop method, sets the event to terminate the thread's main loop"""
		self._stop_event.set()


if __name__ == "__main__":
    main_app = MainApp()

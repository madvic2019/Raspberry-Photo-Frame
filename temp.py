import subprocess
import time
import tempfile
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    
    slide_state = "loading"
    next_check_tm = time.time() + check_dirs
    time_dot=True
    screen = True 
    needs_rescan = False

    if HAS_WATCHDOG:
        class ChangeHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                nonlocal needs_rescan
                if not event.is_directory:
                    needs_rescan = True

        observer = Observer()
        observer.schedule(ChangeHandler(), startdir, recursive=True)
        observer.start()
        logger.info("Inotify observer started for: %s", startdir)
    else:
        logger.warning("watchdog library not found; falling back to periodic polling only")

    ##############################################
    # Setup cache for gelocation information
        slide_state="loading"
        logger.debug("Going to %s",slide_state)
      
      # Lanzar rescan periódico o gatillado por inotify
      if (tm > next_check_tm or needs_rescan) and not scan_in_progress:
          logger.info("Launching background scan (Trigger: %s)", "Inotify" if needs_rescan else "Timer")
          needs_rescan = False
          scan_in_progress = True
          scan_ready_event.clear()   # opcional
          next_check_tm = tm+check_dirs
      DISPLAY.loop_stop()
    except Exception as e:
      logger.error("this was going to fail if previous try failed!")
      
    if HAS_WATCHDOG:
        observer.stop()
        observer.join()
        
    if KEYBOARD:
      kbd.close()
    os.system(CMD_SCREEN_OFF) # turn screen off


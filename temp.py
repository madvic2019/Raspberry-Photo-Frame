
def check_changes(dir): #walk the folder structure to check if there are changes
  global last_file_change
  update = False
  for root, _, _ in os.walk(dir):
    try:
        mod_tm = os.stat(root).st_mtime
        if mod_tm > last_file_change:
          last_file_change = mod_tm
          update = True
    except:
        logger.error("Filesystem not available")
        
  return update

def get_files(dir,config_file,shuffle): # Get image files names to show
  
  global last_file_change
  file_list = None
  extensions = ['.png','.jpg','.jpeg','.bmp'] # can add to these
  if os.path.exists(config_file) : # If there is a previous file list stored, just use it
    logger.info("Config file exists, open for reading %s",config_file)
    with open(config_file, 'r') as f:
        try:
          file_list=json.load(f)
          if len(file_list)>0:
            if len(os.path.commonprefix((file_list[0],dir))) < len(dir) :
              logger.info("Directory is different from config file %s -- %s reloading",os.path.dirname(file_list[0]),dir)
              file_list=None
          else:
            file_list=None
        except:
          logger.warning('%s Config File is not correct',config_file)   
            
  if file_list is None :
    logger.info("Config File is not existing or corrupt")
    logger.info("Clean config file for numbers")
    if os.path.exists(config_file+".num"):
      os.remove(config_file+".num")
    file_list=[]
    for root, _dirnames, filenames in os.walk(dir):
      mod_tm = os.stat(root).st_mtime # time of alteration in a directory
      if mod_tm > last_file_change:
        last_file_change = mod_tm
      for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()
        if ext in extensions and not '.AppleDouble' in root and not filename.startswith('.'):
          file_path_name = os.path.join(root, filename)
          file_list.append(file_path_name) 
        if (len(file_list) % 1000 == 0) : # print every 1000 files detected
          logger.info("%s files",len(file_list)) 
    if shuffle:
      random.shuffle(file_list)
    else:
      file_list.sort() # if not shuffled; sort by name
    
    with open(config_file,'w') as f: #Store list in config file
      json.dump(file_list, f, sort_keys=True)
      logger.info("List written to %s",config_file) 

  logger.info("%d image files found",len(file_list))
  return file_list, len(file_list) # tuple of file list, number of pictures

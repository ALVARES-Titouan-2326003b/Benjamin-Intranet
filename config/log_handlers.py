import os
import datetime
import logging

class DailyDateFileHandler(logging.FileHandler):
    """
    Enregistre les logs dans un fichier différent par jour
    """

    def __init__(self, log_dir, encoding='utf-8'):
        self.log_dir = log_dir
        self.current_date = datetime.date.today()
        filename = self._get_filename(self.current_date)
        
        super().__init__(filename, encoding=encoding, delay=True)

    def _get_filename(self, date_obj):
        return os.path.join(self.log_dir, f"{date_obj.strftime('%Y-%m-%d')}.log")

    def emit(self, record):

        new_date = datetime.date.today()
        if new_date != self.current_date:
            self.current_date = new_date
            self.baseFilename = self._get_filename(self.current_date)
            
            if self.stream:
                self.flush()
                self.stream.close()
                self.stream = None
                            
        super().emit(record)

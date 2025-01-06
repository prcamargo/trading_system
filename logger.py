import logging
import os

class Logger:
    def __init__(self, name: str, log_file: str = "app.log", level: int = logging.INFO):
        """
        Inicializa o logger.

        :param name: Nome do logger.
        :param log_file: Caminho para o arquivo de log.
        :param level: Nível de log (ex: logging.DEBUG, logging.INFO).
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Formatter padrão
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Handler para arquivo
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Adiciona os handlers ao logger
        if not self.logger.hasHandlers():
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        """
        Retorna o logger configurado.
        """
        return self.logger

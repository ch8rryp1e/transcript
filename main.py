import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
import whisper
from moviepy import VideoFileClip
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QProgressBar, QComboBox,
    QFileDialog, QCheckBox, QListWidgetItem, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor


class FileItem:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.status = "Ожидание"
        self.transcription = ""
        self.error_message = ""


class TranscriptionWorker(QThread):
    progress_update = pyqtSignal(int, str, str)
    file_progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, files: List[FileItem], model_name: str, language: Optional[str],
                 task: str, max_workers: int = 2):
        super().__init__()
        self.files = files
        self.model_name = model_name
        self.language = language
        self.task = task
        self.max_workers = max_workers
        self.model = None

    def extract_audio_from_video(self, video_path: str) -> str:
        temp_audio_path = video_path.rsplit('.', 1)[0] + '_temp_audio.wav'
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
            video.close()
            return temp_audio_path
        except Exception as e:
            raise Exception(f"Ошибка извлечения аудио: {str(e)}")

    def transcribe_file(self, file_item: FileItem, index: int) -> None:
        try:
            self.progress_update.emit(index, file_item.file_path, "В процессе")

            file_path = file_item.file_path
            temp_audio_path = None

            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v']
            file_ext = Path(file_path).suffix.lower()

            if file_ext in video_extensions:
                temp_audio_path = self.extract_audio_from_video(file_path)
                audio_path = temp_audio_path
            else:
                audio_path = file_path

            if self.language and self.language != "auto":
                result = self.model.transcribe(
                    audio_path,
                    task=self.task,
                    language=self.language
                )
            else:
                result = self.model.transcribe(
                    audio_path,
                    task=self.task
                )

            file_item.transcription = result["text"]
            file_item.status = "Готово"
            self.progress_update.emit(index, file_item.file_path, "Готово")

            if temp_audio_path and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

        except Exception as e:
            file_item.status = "Ошибка"
            file_item.error_message = str(e)
            self.progress_update.emit(index, file_item.file_path, f"Ошибка: {str(e)}")

            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except:
                    pass

    def run(self):
        try:
            self.progress_update.emit(-1, "Загрузка Whisper...", "Загрузка")
            self.model = whisper.load_model(self.model_name)
            self.progress_update.emit(-1, "Модель загружена", "Готово")

            total_files = len(self.files)
            completed = 0

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.transcribe_file, file_item, idx): idx
                    for idx, file_item in enumerate(self.files)
                }

                for future in as_completed(futures):
                    completed += 1
                    progress_percent = int((completed / total_files) * 100)
                    self.file_progress.emit(progress_percent)

            self.finished.emit()

        except Exception as e:
            self.progress_update.emit(-1, f"Ошибка: {str(e)}", "Ошибка")
            self.finished.emit()


class TranscriberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files: List[FileItem] = []
        self.worker: Optional[TranscriptionWorker] = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Транскрипция Аудио/Видео")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        settings_group = QGroupBox("Настройки")
        settings_layout = QVBoxLayout()

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Модель Whisper:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        settings_layout.addLayout(model_layout)

        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Язык:"))
        self.language_combo = QComboBox()
        languages = [
            "auto", "en", "es", "fr", "de"
        ]
        self.language_combo.addItems(languages)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        settings_layout.addLayout(language_layout)

        self.translate_checkbox = QCheckBox("Перевести на русский")
        settings_layout.addWidget(self.translate_checkbox)

        self.recursive_checkbox = QCheckBox("Рекурсивный поиск в папках")
        settings_layout.addWidget(self.recursive_checkbox)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        file_buttons_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("Добавить файлы")
        self.add_files_btn.clicked.connect(self.add_files)
        file_buttons_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Добавить папку")
        self.add_folder_btn.clicked.connect(self.add_folder)
        file_buttons_layout.addWidget(self.add_folder_btn)

        self.clear_list_btn = QPushButton("Очистить список")
        self.clear_list_btn.clicked.connect(self.clear_list)
        file_buttons_layout.addWidget(self.clear_list_btn)

        main_layout.addLayout(file_buttons_layout)

        main_layout.addWidget(QLabel("Файлы для транскрипции:"))
        self.file_list = QListWidget()
        main_layout.addWidget(self.file_list)

        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout()

        progress_layout.addWidget(QLabel("Общий прогресс:"))
        self.overall_progress = QProgressBar()
        progress_layout.addWidget(self.overall_progress)

        self.status_label = QLabel("Готово")
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        action_buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("Начать ")
        self.start_btn.clicked.connect(self.start_transcription)
        action_buttons_layout.addWidget(self.start_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_transcriptions)
        self.save_btn.setEnabled(False)
        action_buttons_layout.addWidget(self.save_btn)

        main_layout.addLayout(action_buttons_layout)

    def add_files( self):
        file_filter = " файлы (*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm);;Все файлы (*.*)"
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите аудио/видео файлы",
            "",
            file_filter
        )

        for file_path in files:
            if not any(f.file_path == file_path for f in  self.files):
                file_item = FileItem(file_path)
                self.files.append(file_item)
                self.update_file_list()

    def add_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку",
            ""
        )

        if folder_path:
            self.scan_folder( folder_path)
            self.update_file_list ()

    def scan_folder( self, folder_path: str):
        media_extensions = {
            '.mp3', '.wav', '.m4a', '.flac', '.ogg',
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'
        }

        path = Path(folder_path)

        if self.recursive_checkbox.isChecked ():
            files = path.rglob('*')
        else:
            files = path.glob('*')

        for file_path in files:
            if file_path.is_file()  and file_path.suffix.lower () in  media_extensions:
                file_path_str = str(file_path)
                if not any(f.file_path == file_path_str for  f in self.files):
                    file_item = FileItem(file_path_str)
                    self.files.append(file_item)

    def clear_list(self):
        self.files.clear()
        self.file_list.clear()
        self.overall_progress.setValue(0)
        self.status_label.setText("Готово")
        self.save_btn.setEnabled(False)

    def update_file_list(self):
        self.file_list.clear()
        for file_item in self.files:
            item_text = f"{Path(file_item.file_path).name} - {file_item.status}"
            list_item = QListWidgetItem(item_text)

            if file_item.status == "Готово":
                list_item.setForeground(QColor(0, 150, 0))
            elif file_item.status == "В процессе":
                list_item.setForeground(QColor(0, 100, 200))
            elif file_item.status.startswith("Ошибка"):
                list_item.setForeground(QColor(200, 0, 0))

            self.file_list.addItem(list_item)

    def start_transcription(self):
        if not self.files:
            QMessageBox.warning(self, "Нет файлов", "Пожалуйста, добавьте файлы для транскрипции.")
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "В процессе", "Транскрипция уже выполняется.")
            return

        for file_item in self.files:
            file_item.status = "Ожидание"
            file_item.transcription = ""
            file_item.error_message = ""

        self.update_file_list()
        self.overall_progress.setValue(0)
        self.start_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        model_name = self.model_combo.currentText()
        language = self.language_combo.currentText()
        if language == "auto":
            language = None

        task = "translate" if self.translate_checkbox.isChecked() else "transcribe"

        self.worker = TranscriptionWorker(self.files, model_name, language, task)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.file_progress.connect(self.on_file_progress)
        self.worker.finished.connect(self.on_transcription_finished)
        self.worker.start()

    def on_progress_update(self, index: int, file_path: str, status: str):
        if index == -1:
            self.status_label.setText(status)
        else:
            self.files[index].status = status
            self.update_file_list()

    def on_file_progress(self, progress: int):
        self.overall_progress.setValue(progress)

    def on_transcription_finished(self):
        self.start_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText("Транскрипция завершена!")

        done_count = sum(1 for f in self.files if f.status == "Готово")
        error_count = sum(1 for f in self.files if f.status.startswith("Ошибка"))

        QMessageBox.information(
            self,
            "Транскрипциязавершена",
            f"Транскрипция  завершена!\n\nУспешно: {done_count}\nОшибок: {error_count}"
        )

    def save_transcriptions(self):
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения",
            ""
        )

        if not save_dir:  #if otmena
            return

        saved_count = 0
        error_count = 0
        error_messages = []

        for file_item in self.files:
            if file_item.status == "Готово" and file_item.transcription:
                try:
                    original_name = Path(file_item.file_path).stem
                    output_path = Path(save_dir) / f"{original_name}_transcription.txt"

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(file_item.transcription)

                    saved_count += 1
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Ошибка сохранения {file_item.file_path}: {e}")



        QMessageBox.information(
            self,
            "Сохранение завершено",
            f"Сохранено транскрипций: { saved_count}\n"
            f"Ошибок: {error_count}"
        )


def main():
    app = QApplication(sys.argv)
    window = TranscriberApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
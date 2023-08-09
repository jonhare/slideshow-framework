import cv2
from kivy import Logger
from kivy.core.camera.camera_opencv import CameraOpenCV
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.camera import Camera
from kivy.uix.floatlayout import FloatLayout

from . import Slide

MAX_DEVICES = 10


class MyOpenCVCamera(CameraOpenCV):
    def __init__(self, processor=None, **kwargs):
        super().__init__(**kwargs)
        self.processor = processor

    @staticmethod
    def list_devices():
        index = 0
        arr = []
        i = MAX_DEVICES
        while i > 0:
            cap = cv2.VideoCapture(index)
            if cap.read()[0]:
                arr.append(index)
                cap.release()
            index += 1
            i -= 1
        return arr

    def _update(self, dt):
        if self.stopped:
            return
        if self._texture is None:
            # Create the texture
            self._texture = Texture.create(self._resolution)
            self._texture.flip_vertical()
            self.dispatch('on_load')
        try:
            ret, frame = self._device.read()

            if self.processor:
                frame = self.processor(frame)

            self._format = 'bgr'
            try:
                self._buffer = frame.imageData
            except AttributeError:
                # frame is already of type ndarray
                # which can be reshaped to 1-d.
                self._buffer = frame.reshape(-1)

            self._copy_to_gpu()
        except:
            Logger.exception('OpenCV: Couldn\'t get image from Camera')


class MyUIXCamera(Camera):
    processor = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fbind('processor', self._on_processor)

    def _on_processor(self, *args):
        if self._camera is not None:
            self._camera.processor = self.processor

    def _on_index(self, *args):
        self._camera = None
        if self.index < 0:
            return
        if self.resolution[0] < 0 or self.resolution[1] < 0:
            self._camera = MyOpenCVCamera(processor=self.processor, index=self.index, stopped=True)
        else:
            self._camera = MyOpenCVCamera(processor=self.processor, index=self.index,
                                          resolution=self.resolution, stopped=True)
        if self.play:
            self._camera.start()

        self._camera.bind(on_texture=self.on_tex)


Builder.load_string('''
<VCSpinnerOption@SpinnerOption>:
    height: "30dp"

<VideoCaptureWidget>:
    BoxLayout:
        orientation: 'vertical'
        MyUIXCamera:
            id: camera_view
            fit_mode: 'contain'
            size_hint: (1, 0.95)
            index: -1 if len(_camera_index.text) == 0 else int(_camera_index.text)
            play: True
            processor: root.processor
        AnchorLayout:
            anchor_x: 'center'
            anchor_y: 'bottom'
            size_hint: (1, 0.05)
            Spinner:
                id: _camera_index
                text: '-1' if len(root.cams) == 0 else root.cams[0]
                values: root.cams
                size_hint: (0.5, 1)
                option_cls: 'VCSpinnerOption'
''')


class VideoCaptureWidget(FloatLayout):
    processor = ObjectProperty(None)
    cams = ObjectProperty([str(x) for x in MyOpenCVCamera.list_devices()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class VideoCaptureSlide(Slide):
    def __init__(self, processor=None, **kwargs):
        super().__init__(**kwargs)

        self.processor = processor

    def build(self):
        self.add_widget(VideoCaptureWidget(processor=self.processor))

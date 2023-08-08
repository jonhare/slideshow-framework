from io import BytesIO

import kivy
from PIL import Image
from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as kiImage
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition, TransitionBase
from kivy.uix.video import Video

kivy.require('2.2.1')


def pil_to_kivy(canvas_img):
    data = BytesIO()
    canvas_img.save(data, format='png')
    data.seek(0)
    im = CoreImage(BytesIO(data.read()), ext='png')
    return im


class Slide(Screen):
    next_transition = ObjectProperty(baseclass=TransitionBase)
    prev_transition = ObjectProperty(baseclass=TransitionBase)
    ignore_keyboard = BooleanProperty(defaultvalue=False)

    def build(self):
        return None

    def close(self):
        pass

    def on_key_down(self, keyboard, keycode, text, modifiers):
        pass

    def on_pre_enter(self):
        self.add_widget(self.build())

    def on_leave(self, *args):
        self.remove_widget(self.children[0])


class PictureSlide(Slide):
    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self.image = image

    def build(self):
        if isinstance(self.image, str):
            img = kiImage(source=self.image, fit_mode="contain", pos=(0, 0), pos_hint={'x': 0, 'y': 0})
        elif isinstance(self.image, Image.Image):
            img = kiImage(fit_mode="contain", pos=(0, 0), pos_hint={'x': 0, 'y': 0})
            img.texture = pil_to_kivy(self.image).texture
        else:
            raise Exception("unsupported type")
        return img


class AudioVideoSlide(Slide):
    def __init__(self, video, repeat=False, volume=1., **kwargs):
        super().__init__(**kwargs)

        self.video = Video(source=video, fit_mode='contain', volume=volume)
        if repeat:
            video.options = {'eos': 'loop'}

    def build(self):
        self.video.state = 'play'
        return self.video

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'spacebar':
            if self.video.state == 'play':
                self.video.state = 'pause'
            else:
                self.video.state = 'play'


class VideoSlide(AudioVideoSlide):
    def __init__(self, video, repeat=False, **kwargs):
        super().__init__(video, repeat=repeat, volume=0, **kwargs)

    # def close(self):
    #     self.cam.play = False
    #     # self.cam._camera._device.release() #perhaps speed up release rather than waiting on gc?
    #     self.cam.index = -1


def set_fullscreen(fullscreen):
    Window.fullscreen = fullscreen


def toggle_fullscreen():
    if Window.fullscreen == 0:
        Window.fullscreen = 'auto'
    else:
        Window.fullscreen = 0


class Slideshow(App):
    def __init__(self, slides, background_image=None, default_transition: TransitionBase = NoTransition()):
        super().__init__()

        self.hidden = False
        self.slides = slides
        self.current_slide_index = -1
        self.current_slide = None
        self.default_transition = default_transition

        self.root = FloatLayout()
        layout = FloatLayout()
        self.root.add_widget(layout)

        if background_image is not None:
            bg = PictureSlide(background_image).build()
            layout.add_widget(bg)

        self.sm = ScreenManager()
        layout.add_widget(self.sm)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self.root, 'text')
        self._keyboard.bind(on_key_down=self.on_key_down)

        self.display_next_slide()

    def _keyboard_closed(self):
        pass

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if self.current_slide.ignore_keyboard:
            return True

        if keycode[1] == 'left' or keycode[1] == 'pageup' or keycode[1] == 'up':
            if not self.hidden:
                self.display_prev_slide()
        elif keycode[1] == 'right' or keycode[1] == 'pagedown' or keycode[1] == 'down':
            if not self.hidden:
                self.display_next_slide()
        elif keycode[1] == 'f' or keycode[1] == 'f5':
            toggle_fullscreen()
        elif keycode[1] == 'escape':
            set_fullscreen(False)
        elif keycode[1] == 'b':
            self.toggle_hidden()
        elif keycode[1] == 'q':
            App.get_running_app().stop()

        self.current_slide.on_key_down(keyboard, keycode, text, modifiers)

        return True

    def display_next_slide(self):
        if self.current_slide_index < len(self.slides) - 1:
            self.current_slide_index += 1
            next_slide = self.slides[self.current_slide_index]
            if self.current_slide is None or self.current_slide.next_transition is None:
                self.sm.switch_to(next_slide, transition=self.default_transition, direction='left')
            else:
                self.sm.switch_to(next_slide, transition=self.current_slide.next_transition)
            self.current_slide = next_slide

    def display_prev_slide(self):
        if self.current_slide_index > 0:
            self.current_slide_index -= 1
            next_slide = self.slides[self.current_slide_index]
            if self.current_slide is None or self.current_slide.prev_transition is None:
                self.sm.switch_to(next_slide, transition=self.default_transition, direction='right')
            else:
                self.sm.switch_to(next_slide, transition=self.current_slide.prev_transition)
            self.current_slide = next_slide

    def toggle_hidden(self):
        if self.hidden:
            self.sm.switch_to(self.current_slide, transition=NoTransition())
        else:
            sc = Screen()
            sc.add_widget(kiImage(fit_mode='fill', color=[0, 0, 0, 1]))
            self.sm.switch_to(sc, transition=NoTransition())
        self.hidden = not self.hidden

    def build(self):
        return self.root

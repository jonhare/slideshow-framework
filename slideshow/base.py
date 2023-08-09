from io import BytesIO

import kivy
from PIL import Image
from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.properties import ObjectProperty, BooleanProperty, NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as kiImage
from kivy.uix.relativelayout import RelativeLayout
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
        pass

    def close(self):
        pass

    def on_key_down(self, keyboard, keycode, text, modifiers):
        pass

    def on_pre_enter(self):
        self.build()

    def on_leave(self, *args):
        self.close()
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
            raise Exception("unsupported type", type(self.image))

        self.add_widget(img)


class WrapperSlide(Slide):
    def __init__(self, background, slide, **kwargs):
        super().__init__(**kwargs)

        self.background = background
        self.slide = slide
        self.slide.bind(ignore_keyboard=self.setter('ignore_keyboard'))
        self.ignore_keyboard = self.slide.ignore_keyboard

    def build(self):
        img = PictureSlide(self.background)
        img.build()

        slide = self.slide
        slide.parent = None
        slide.build()

        layout = FloatLayout()
        layout.add_widget(img)
        layout.add_widget(slide)

        self.add_widget(layout)

    def close(self):
        self.slide.close()

    def on_key_down(self, keyboard, keycode, text, modifiers):
        self.slide.on_key_down(keyboard, keycode, text, modifiers)


class AudioVideoSlide(Slide):
    def __init__(self, video, repeat=False, volume=1., **kwargs):
        super().__init__(**kwargs)

        self.video = video
        self.repeat = repeat
        self.volume = volume

    def build(self):
        video = Video(source=self.video, fit_mode='contain', volume=self.volume)
        if self.repeat:
            video.options = {'eos': 'loop'}
        video.state = 'play'
        self.add_widget(video)

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'spacebar':
            if self.video.state == 'play':
                self.video.state = 'pause'
            else:
                self.video.state = 'play'


class VideoSlide(AudioVideoSlide):
    def __init__(self, video, repeat=False, **kwargs):
        super().__init__(video, repeat=repeat, volume=0, **kwargs)


def set_fullscreen(fullscreen):
    Window.fullscreen = fullscreen


def toggle_fullscreen():
    if Window.fullscreen == 0:
        Window.fullscreen = 'auto'
    else:
        Window.fullscreen = 0


# class FixedAspectFloatLayout(FloatLayout):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#
#         self.bind(height=self.calc_height)
#         self.bind(parent=self.calc_height)
#
#     def calc_height(self, *args, **kwargs):
#         print("width", self.width, "height",self.height)
#         self.height = self.width * 0.5


class ARLayout(RelativeLayout):
    # based on https://stackoverflow.com/a/28738057
    ratio = NumericProperty(10. / 16.)

    def do_layout(self, *args):
        for child in self.children:
            self.apply_ratio(child)
        super(ARLayout, self).do_layout()

    def apply_ratio(self, child):
        # ensure the child don't have specification we don't want
        child.size_hint = None, None
        child.pos_hint = {"center_x": .5, "center_y": .5}

        # calculate the new size, ensure one axis doesn't go out of the bounds
        w, h = self.size
        h2 = w * self.ratio
        if h2 > self.height:
            w = h / self.ratio
        else:
            h = h2
        child.size = w, h


class Slideshow(App):
    def __init__(self, slides, slide_width, slide_height, background_image=None,
                 default_transition: TransitionBase = NoTransition()):
        super().__init__()

        self.hidden = False
        self.slides = slides
        self.current_slide_index = -1
        self.current_slide = None
        self.default_transition = default_transition

        self.root = ARLayout(
            ratio=float(slide_height) / float(slide_width))  # root layout has fixed aspect ratio within window

        layout = FloatLayout()  # FloatLayout to allow overlapping bg
        self.root.add_widget(layout)

        if background_image is not None:
            bg = PictureSlide(background_image, pos_hint={'x': 0, 'y': 0})
            bg.build()
            layout.add_widget(bg)

        self.sm = ScreenManager(pos_hint={'x': 0, 'y': 0})
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

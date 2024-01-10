from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
import cv2
import numpy as np
import math
from pathlib import Path
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.core.window import Window

Window.size = (300, 600)

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.username = TextInput(hint_text='Username', multiline=False, size_hint=(0.5, 0.1), pos_hint={'x': 0.1, 'y': 0})
        self.password = TextInput(hint_text='Password', multiline=False, password=True, size_hint=(0.5, 0.1), pos_hint={'x': 0.1, 'y': 0})
        box = BoxLayout(orientation='vertical')
        #box.add_widget(Image(source=r"C:\Users\mitul\OneDrive\GolfApp\logo.jpeg"))  # Add the logo at the top

        # Create a new BoxLayout for the username and password fields
        credentials_box = BoxLayout(orientation='horizontal')
        credentials_box.add_widget(self.username)
        credentials_box.add_widget(self.password)

        box.add_widget(credentials_box)
        box.add_widget(Button(text='Login', on_press=self.verify_credentials, size_hint=(1, 0.1), pos_hint={'x': 0, 'y': 0}))
        self.add_widget(box)

    def verify_credentials(self, instance):
        username = self.username.text
        password = self.password.text
        if username == 'test' and password == 'test':
            self.manager.current = 'how_to_use'
        else:
            print("Invalid username or password")




class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super(HomeScreen, self).__init__(**kwargs)
        box = BoxLayout(orientation='vertical')
        box.add_widget(Button(text='How to use', on_press=self.go_to_how_to_use))
        box.add_widget(Button(text='Track', on_press=self.go_to_track))
        box.add_widget(Button(text='History and Settings', on_press=self.go_to_history_settings))
        self.add_widget(box)

    def go_to_how_to_use(self, instance):
        self.manager.current = 'how_to_use'

    def go_to_track(self, instance):
        self.manager.current = 'track'

    def go_to_history_settings(self, instance):
        self.manager.current = 'history_settings'


class HowToUseScreen(Screen):
    pass


class TrackScreen(Screen):
    def on_pre_enter(self):
        self.ids.output_label.text = ''

    def upload_video(self, instance):
        club = self.ids.club_input.text
        video_path = self.ids.video_path_input.text.strip('"')
        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        scale = 0.005
        g = -9.81
        backSub = cv2.createBackgroundSubtractorMOG2()
        ret, frame = cap.read()
        if not ret:
            self.output_label.text += "Can't receive frame (stream end?). Exiting ...\n"
            exit()
        frame = cv2.resize(frame, (600, 600))
        roi = (267, 455, 328, 137)
        min_contour_area = 90
        max_contour_area = 100
        aspect_ratio_tolerance = 0.2
        center_points = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
    
            # Resize frame
            frame = cv2.resize(frame, (600, 600))

            # Apply the background subtractor to get the foreground mask
            fgMask = backSub.apply(frame)

            # Find contours in the foreground mask
            contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
            for contour in contours:
                # Filter contours based on their area
                if min_contour_area < cv2.contourArea(contour) < max_contour_area:
                    # Get the bounding box of the contour
                    x, y, w, h = cv2.boundingRect(contour)

                    # Check if the bounding box is approximately square
                    aspect_ratio = float(w)/h
                    if 1 - aspect_ratio_tolerance < aspect_ratio < 1 + aspect_ratio_tolerance:

                        # Check if the bounding box is within the ROI
                        if roi[0] < x and x + w < roi[0] + roi[2] and roi[1] < y and y + h < roi[1] + roi[3]:
                            # Check if the bounding box is within the frame boundaries
                            if 0 <= x <= frame.shape[1] and 0 <= y <= frame.shape[0]:
                                # Draw the bounding box on the frame
                                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
                                # Calculate the center point of the bounding box
                                center_point = (int(x + w/2), int(y + h/2))
                                center_points.append(center_point)

            # Draw the path of the object
            for i in range(1, len(center_points)):
                cv2.line(frame, center_points[i - 1], center_points[i], (0, 0, 255), 2)

            # Display the resulting frame and the foreground mask
            cv2.imshow('Frame', frame)
            #cv2.imshow('FG Mask', fgMask)

            keyboard = cv2.waitKey(1)
            if keyboard == 'q' or keyboard == 27:
                break
        # Calculate the initial velocity as the ball is hit
        if len(center_points) > 1:
            # Find the first position where the ball has moved a significant amount
            for i in range(1, len(center_points)):
                dx = center_points[i][0] - center_points[0][0]
                dy = center_points[i][1] - center_points[0][1]
                if np.sqrt(dx**2 + dy**2) > 5:  # adjust this value as needed
                    break

            # Calculate the initial velocity (in meters per frame)
            dt = i / fps
            v0 = scale * np.sqrt(dx**2 + dy**2) / dt

            # Convert the velocity to meters per second
            v0_mps = v0 * fps

            # Convert the velocity to kmph
            v0_kmph = v0_mps * 3.6

            # Convert the velocity to mph
            v0_mph = v0_mps * 2.237

            # Calculate the angle in radians
            angle_radians = math.atan2(dy, dx)
    
            # Convert the angle to degrees
            angle_degrees = math.degrees(angle_radians)
    
    
            # Calculate the flight time in seconds
            t = 2 * v0_mps * math.sin(angle_radians) / g
    
            # Calculate the apex of the curve in meters
            h = v0_mps**2 * math.sin(angle_radians)**2 / (2 * g)
        
            # Calculate the horizontal distance travelled in meters
            d = v0_mps**2 * math.sin(2 * angle_radians) / g        

        self.ids.output_label.text += f"The estimated launch angle is {-round(angle_degrees, 1)} degrees\n"
        self.ids.output_label.text += f"The estimated initial velocity is {round(v0_kmph, 1)} km/h or {round(v0_mph, 1)} mph\n"
        self.ids.output_label.text += f"The estimated flight time is {round(t, 1)} seconds\n"
        self.ids.output_label.text += f"The estimated apex of the curve is {-round(h, 1)} meters\n"
        self.ids.output_label.text += f"The estimated horizontal distance travelled is {round(d, 1)} meters\n"
        cap.release()
        cv2.destroyAllWindows()



    pass

class HistorySettingsScreen(Screen):
    pass

class MyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(HowToUseScreen(name='how_to_use'))
        sm.add_widget(TrackScreen(name='track'))
        sm.add_widget(HistorySettingsScreen(name='history_settings'))
        return sm

if __name__ == '__main__':
    MyApp().run()

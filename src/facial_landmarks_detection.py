
from openvino.inference_engine import IENetwork, IECore
import numpy as np
import cv2

class ModelLandmarksDetection:
    '''
    Class for the Landmarks Detection Model.
    '''

    def __init__(self, model_name, device='CPU', extensions=None):
        '''
        Set instance variables.
        '''
        self.model_weights=model_name+'.bin'
        self.model_structure=model_name+'.xml'
        self.device=device
        self.extensions=extensions

        self.plugin = IECore()

        try:
            self.model=self.plugin.read_network(self.model_structure, self.model_weights)
        except Exception as e:
            raise ValueError("Could not Initialise the network. Have you enterred the correct model path?")

        self.input_name=next(iter(self.model.inputs))
        self.input_shape=self.model.inputs[self.input_name].shape
        self.output_name=next(iter(self.model.outputs))
        self.output_shape=self.model.outputs[self.output_name].shape

    def load_model(self):
        '''
        Loading model in core
        '''
        self.check_model()
        if self.extensions:
            self.plugin.add_extension(self.extensions,self.device)
        self.exec_network = self.plugin.load_network(network=self.model, device_name=self.device)

    def check_model(self):
        '''
        Checking for unsupported layers
        '''
        # Check for any unsupported layers, and let the user
        # know if anything is missing. Exit the program, if so
        supported_layers = self.plugin.query_network(network=self.model, device_name=self.device)
        unsupported_layers = [l for l in self.model.layers.keys() if l not in supported_layers]
        if len(unsupported_layers) != 0:
            print("Unsupported layers found: {}".format(unsupported_layers))
            print("Check whether extensions are available to add to IECore.")
            exit(1)

    def predict(self, face, coord, origin_image):
        '''
        Detecting landmarks in face

        :image: face to predict
        :coord: start coordinate of the detected face in the origin_image
        :origin_image: original image
        :return: eyes: right and left eye
                 landmarks[0:4]: center of right and left eye
                 preprocessed_image: image with detected landmarks
        '''
        preprocessed_input = self.preprocess_input(face)

        self.exec_network.infer({self.input_name:preprocessed_input})

        result = self.exec_network.requests[0]

        landmarks = result.outputs[self.output_name][0].flatten().tolist()
        height, width = face.shape[:2]
        for i in range(len(landmarks)):
            if (i%2==0):
                landmarks[i] = (int) (landmarks[i]*width + coord[0])
            else:
                landmarks[i] = (int) (landmarks[i]*height + coord[1])

        #DEBUG drawing landmarks
        preprocessed_image, eyes = self.draw_output(landmarks, origin_image)

        return eyes, landmarks[0:4], preprocessed_image

    def draw_output(self, output, image):
        '''
        Drawing circle around detected landmarks and rectangle around eyes
        '''
        landmarks = [int(i) for i in output]
        (x_lefteye, y_lefteye) = landmarks[0:2]
        (x_righteye, y_righteye) = landmarks[2:4]
        (x_nose, y_nose) = landmarks[4:6]
        (x_leftcorner, y_leftcorner) = landmarks[6:8]
        (x_rightcorner, y_rightcorner) = landmarks[8:10]

        r=25

        # in case the face is too near the border
        # which leads the the error if the modified coord is negative or bigger than width/height, set them to 0 or width/height corresponding
        height, width = image.shape[:2]
        cut_y_lefteye_start=y_lefteye-r if (y_lefteye-r)>0 else 0
        cut_y_lefteye_end=y_lefteye+r if (y_lefteye+r)<height else height
        cut_x_lefteye_start=x_lefteye-r if (x_lefteye-r)>0 else 0
        cut_x_lefteye_end=x_lefteye+r if (x_lefteye+r)<width else width
        cut_y_righteye_start=y_righteye-r if (y_righteye-r)>0 else 0
        cut_y_righteye_end=y_righteye+r if (y_righteye+r)<height else height
        cut_x_righteye_start=x_righteye-r if (x_righteye-r)>0 else 0
        cut_x_righteye_end=x_righteye+r if (x_righteye+r)<width else width

        eyes = (image[cut_y_lefteye_start:cut_y_lefteye_end,cut_x_lefteye_start:cut_x_lefteye_end].copy(),
                image[cut_y_righteye_start:cut_y_righteye_end,cut_x_righteye_start:cut_x_righteye_end].copy())

        cv2.rectangle(image, (x_lefteye-r, y_lefteye-r), (x_lefteye+r, y_lefteye+r), (255,0,0), 1)
        cv2.rectangle(image, (x_righteye-r, y_righteye-r), (x_righteye+r, y_righteye+r), (255,0,0), 1)
        cv2.circle(image, (x_nose, y_nose), 5, (255,0,0), -1)
        cv2.circle(image, (x_leftcorner, y_leftcorner), 5, (255,0,0), -1)
        cv2.circle(image, (x_rightcorner, y_rightcorner), 5, (255,0,0), -1)

        return image, eyes

    def preprocess_input(self, image):
        '''
        Preprocessing the input to fit the the inference engine
        '''
        b, c, h, w = self.input_shape
        prepo = np.copy(image)
        prepo = cv2.resize(prepo, (w,h))
        prepo = prepo.transpose((2,0,1))
        prepo = prepo.reshape(1,c,h,w)
        return prepo

import io
import unittest
from unittest.mock import patch
from PIL import Image
from isolated_application import load_isolated_application


class HeifInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application('_heif_input_test')

    def sample(self):
        buffer = io.BytesIO()
        Image.new('RGB', (320, 240), (90,130,170)).save(buffer, format='HEIF', quality=90)
        return buffer.getvalue()

    def test_actual_heic_bytes_decode_without_disk(self):
        image, fmt, width, height = self.module._opened_image(self.sample(), 'synthetic.heic')
        self.assertEqual((fmt,width,height,image.mode),('HEIF',320,240,'RGB'))

    def test_mislabeled_and_broken_heic_reject(self):
        for data, filename in [(self.sample(),'wrong.png'),(b'not a valid HEIC','broken.heic')]:
            with self.assertRaises(self.module.ImageValidationError):
                self.module._opened_image(data,filename)

    def test_pixel_limit_before_rgb_conversion(self):
        with patch.object(self.module,'MAX_IMAGE_PIXELS',100):
            with self.assertRaises(self.module.ImageValidationError):
                self.module._opened_image(self.sample(),'synthetic.heic')

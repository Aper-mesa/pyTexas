import os

from Cython.Build import cythonize
from Cython.Distutils import build_ext
from setuptools import setup, Extension

# python setup.py build_ext --inplace

STEAM_SDK_PATH = os.path.join("resources", "sdk")


class custom_build_ext(build_ext):
    def build_extensions(self):
        self.compiler.add_include_dir(self.build_temp)
        build_ext.build_extensions(self)


ext_modules = [
    Extension(
        "steam_wrapper",
        sources=["steam_wrapper.pyx", "steam_callback_helpers.cpp"],
        include_dirs=[
            os.path.join(STEAM_SDK_PATH, "public/steam"),
            "."
        ],
        library_dirs=[
            os.path.join(STEAM_SDK_PATH, "redistributable_bin", "win64")
        ],
        libraries=["steam_api64"],
        language="c++"
    )
]

setup(
    ext_modules=cythonize(ext_modules, compiler_directives={'language_level': "3"}),
    cmdclass={'build_ext': custom_build_ext}
)

import os
from setuptools import setup, find_packages, Extension
import platform
import sys
from setuptools.command.build_ext import build_ext

# Đọc các dependencies từ requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Kiểm tra nền tảng hệ điều hành
is_windows = platform.system() == 'Windows'

# Lớp xử lý quá trình biên dịch mở rộng
class BuildExt(build_ext):
    def build_extensions(self):
        # Phát hiện trình biên dịch C++ và đặt cờ phù hợp
        compiler_type = self.compiler.compiler_type
        
        for ext in self.extensions:
            if compiler_type == 'msvc':  # Windows với MSVC
                ext.extra_compile_args = ['/std:c++14', '/EHsc', '/O2']
            else:  # GCC/Clang trên Linux/Mac
                ext.extra_compile_args = ['-std=c++14', '-O3']
                if sys.platform == 'darwin':  # macOS
                    ext.extra_compile_args.append('-stdlib=libc++')
            
            # Thêm include_dirs cho các thư viện phổ biến
            import numpy
            ext.include_dirs.append(numpy.get_include())
            
        super().build_extensions()

# Kiểm tra xem pybind11 đã được cài đặt chưa
try:
    import pybind11
    pybind11_include = pybind11.get_include()
    have_pybind11 = True
except ImportError:
    pybind11_include = ""
    have_pybind11 = False

# Khai báo extension modules
extensions = []

# Chỉ thêm C++ extensions nếu QUANGSTATION_SKIP_CPP không được đặt
if not os.environ.get('QUANGSTATION_SKIP_CPP') and have_pybind11:
    # Module tính toán liều C++
    dose_engine_module = Extension(
        'quangstation.dose_calculation._dose_engine',
        sources=['quangstation/dose_calculation/dose_engine.cpp'],
        include_dirs=[pybind11_include],
    )
    extensions.append(dose_engine_module)

    # Module tối ưu C++
    optimizer_module = Extension(
        'quangstation.optimization._optimizer',
        sources=['quangstation/optimization/optimizer.cpp'],
        include_dirs=[pybind11_include],
    )
    extensions.append(optimizer_module)

# Đọc mô tả dài từ README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="quangstation",
    version="2.0.0",
    author="Mạc Đăng Quang",
    author_email="quangmacdang@gmail.com",
    description="Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quangmac/QuangStationV2",
    packages=find_packages(),
    ext_modules=extensions,
    cmdclass={'build_ext': BuildExt},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "quangstation=quangstation.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "quangstation": ["resources/**/*"],
    },
) 
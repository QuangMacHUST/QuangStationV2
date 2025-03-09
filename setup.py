import os
from setuptools import setup, find_packages, Extension
import platform

# Đọc các dependencies từ requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Kiểm tra nền tảng hệ điều hành
is_windows = platform.system() == 'Windows'

# Khai báo extension modules
extensions = []

# Module tính toán liều C++
dose_engine_module = Extension(
    'quangstation.dose_calculation._dose_engine',
    sources=[
        'quangstation/dose_calculation/dose_engine.cpp',
    ],
    include_dirs=[],
    extra_compile_args=['-std=c++14'] if not is_windows else ['/std:c++14'],
)
extensions.append(dose_engine_module)

# Module tối ưu C++
optimizer_module = Extension(
    'quangstation.optimization._optimizer',
    sources=[
        'quangstation/optimization/optimizer.cpp',
    ],
    include_dirs=[],
    extra_compile_args=['-std=c++14'] if not is_windows else ['/std:c++14'],
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
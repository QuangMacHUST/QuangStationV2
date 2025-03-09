"""
Module chứa các widget tùy chỉnh cho giao diện người dùng QuangStation.
"""

from quangstation.gui.widgets.image_viewer import ImageViewer

__all__ = ['ImageViewer']

# Thêm Viewer3D nếu VTK được cài đặt
try:
    from quangstation.gui.widgets.viewer_3d import Viewer3D
    __all__.append('Viewer3D')
except ImportError:
    pass 
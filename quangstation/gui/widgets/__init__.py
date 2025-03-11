"""
Module chứa các widget tùy chỉnh cho QuangStation V2.
"""

# Import các widget
try:
    from quangstation.gui.widgets.image_viewer import ImageViewer
except ImportError:
    pass

try:
    from quangstation.gui.widgets.viewer_3d import Viewer3D
except ImportError:
    pass

try:
    from quangstation.gui.widgets.dvh_viewer import DVHViewer
except ImportError:
    pass

try:
    from quangstation.gui.widgets.mpr_viewer import MPRViewer
except ImportError:
    pass

# Export các widget
__all__ = ['ImageViewer', 'Viewer3D', 'DVHViewer', 'MPRViewer'] 
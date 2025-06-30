import Part

def create_insert():
    frame = Part.makeBox(10, 5, 2)  # Length, Width, Height
    frame_feature = Part.show(frame, 'game box')
    frame_feature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

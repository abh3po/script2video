extends MeshInstance3D

var t := 0.0

func _process(delta: float) -> void:
	t += delta
	rotation.y = t * 1.2
	rotation.x = sin(t * 0.9) * 0.5
	position.y = sin(t * 1.4) * 0.35

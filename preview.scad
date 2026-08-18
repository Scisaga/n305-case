$fn=96;
// 预览：底壳、顶部防撞框、风扇网框和按钮
color([0.72,0.72,0.74]) import("n305_case_bottom.stl");
color([0.55,0.55,0.58]) import("n305_case_top_bumper_frame.stl");
translate([-0.2,-3.45,25.9]) color([0.35,0.35,0.38]) import("n305_fan_mesh_frame_A.stl");
translate([-18,-56.4,6.5]) color([0.65,0.65,0.67]) import("n305_power_button_adjustable.stl");

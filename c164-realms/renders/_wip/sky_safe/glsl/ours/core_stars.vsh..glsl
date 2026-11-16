#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _22;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _29;

layout(location = 0) in vec3 Position;
out vec3 c164_star;

void main()
{
    gl_Position = (_22.ProjMat * _29.ModelViewMat) * vec4(mat3(vec3(1.0, 0.0, 0.0), vec3(0.0, 0.017558999359607696533203125, -0.999845981597900390625), vec3(0.0, 0.999845981597900390625, 0.017558999359607696533203125)) * Position, 1.0);
    c164_star = mat3(vec3(0.0, 0.0, 1.0), vec3(-0.7313539981842041015625, -0.6819980144500732421875, 0.0), vec3(0.6819980144500732421875, -0.7313539981842041015625, -0.0)) * Position;
}


// Soft round contact shadow (multiplied) and coloured UI-in-world markers (alpha-blended) on a quad.
Shader "TinyTracks/Blob"
{
    Properties
    {
        _BaseColor ("Colour", Color) = (0,0,0,0.35)
        _Softness ("Softness", Range(0.01,1)) = 0.6
        _Ring ("Ring (0 = disc)", Range(0,1)) = 0
        _Pulse ("Pulse", Range(0,1)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent-50" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Offset -1, -1
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor; half _Softness; half _Ring; half _Pulse;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            V vert(A i) { V o; UNITY_SETUP_INSTANCE_ID(i); o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.uv = i.uv * 2 - 1; return o; }
            half4 frag(V i) : SV_Target
            {
                half r = length(i.uv);
                half a = 1.0h - smoothstep(1.0h - _Softness, 1.0h, r);
                if (_Ring > 0) a *= smoothstep(_Ring - 0.15h, _Ring, r);
                half p = 1.0h - _Pulse * 0.35h * (0.5h + 0.5h * sin(_Time.y * 5.0h));
                return half4(_BaseColor.rgb, _BaseColor.a * a * p);
            }
            ENDHLSL
        }
    }
}

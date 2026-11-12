// Skybox: soft vertical gradient (horizon -> zenith) with a warm sun glow.
Shader "TinyTracks/SkyGradient"
{
    Properties
    {
        _Top ("Zenith", Color) = (0.36,0.68,1,1)
        _Horizon ("Horizon", Color) = (0.82,0.93,1,1)
        _Bottom ("Below horizon", Color) = (0.72,0.88,0.75,1)
        _SunColor ("Sun glow", Color) = (1,0.95,0.8,1)
        _SunDir ("Sun direction", Vector) = (0.3,0.6,-0.7,0)
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _Top; half4 _Horizon; half4 _Bottom; half4 _SunColor; float4 _SunDir;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; };
            struct V { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };
            V vert(A i) { V o; o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.dir = i.positionOS.xyz; return o; }
            half4 frag(V i) : SV_Target
            {
                float3 d = normalize(i.dir);
                half up = d.y;
                half3 col = up >= 0 ? lerp(_Horizon.rgb, _Top.rgb, pow(saturate(up), 0.6h)) : lerp(_Horizon.rgb, _Bottom.rgb, saturate(-up * 4));
                half s = saturate(dot(d, normalize(_SunDir.xyz)));
                col += _SunColor.rgb * (pow(s, 64.0h) * 0.6h + pow(s, 6.0h) * 0.12h);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
}

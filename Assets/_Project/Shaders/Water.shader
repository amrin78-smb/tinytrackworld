// Lake water: gentle vertex waves, depth-free colour gradient by vertex colour alpha (shore = 0 -> deep = 1), sparkles.
Shader "TinyTracks/Water"
{
    Properties
    {
        _Shallow ("Shallow", Color) = (0.55,0.88,0.95,1)
        _Deep ("Deep", Color) = (0.18,0.55,0.86,1)
        _WaveHeight ("Wave height", Float) = 0.04
        _WaveSpeed ("Wave speed", Float) = 1.2
        _Sparkle ("Sparkle", Range(0,1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry+10" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "Water"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _Shallow; half4 _Deep; float _WaveHeight; float _WaveSpeed; half _Sparkle;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; half4 color : COLOR; };
            struct V { float4 positionCS : SV_POSITION; float3 p : TEXCOORD0; half depth : TEXCOORD1; half fog : TEXCOORD2; };
            V vert(A i)
            {
                V o;
                float3 w = TransformObjectToWorld(i.positionOS.xyz);
                float t = _Time.y * _WaveSpeed;
                w.y += (sin(w.x * 0.9 + t) + sin(w.z * 1.3 - t * 1.1)) * _WaveHeight * i.color.a;
                o.p = w;
                o.positionCS = TransformWorldToHClip(w);
                o.depth = i.color.a;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float t = _Time.y * _WaveSpeed;
                half3 col = lerp(_Shallow.rgb, _Deep.rgb, saturate(i.depth));
                half ripple = sin(i.p.x * 3.1 + t * 1.7) * sin(i.p.z * 2.7 - t * 1.3);
                half sparkle = smoothstep(0.92h, 1.0h, ripple) * _Sparkle * saturate(i.depth * 2);
                half foam = smoothstep(0.12h, 0.0h, i.depth) * (0.6h + 0.4h * sin(t * 2 + i.p.x * 2));
                Light l = GetMainLight();
                col = col * (0.75h + 0.35h * l.color) + sparkle + foam * 0.6h;
                col = MixFog(col, i.fog);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
}

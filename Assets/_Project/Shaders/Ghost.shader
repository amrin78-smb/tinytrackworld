// Placement preview: translucent tinted copy of a model with a pulsing fresnel edge. _BaseColor = green (valid) / red (invalid).
Shader "TinyTracks/Ghost"
{
    Properties
    {
        _BaseColor ("Colour", Color) = (0.3,1,0.4,0.45)
        _Pulse ("Pulse", Range(0,1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "Ghost"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                half _Pulse;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; half4 color : COLOR; };
            struct V { float4 positionCS : SV_POSITION; float3 n : TEXCOORD0; float3 p : TEXCOORD1; half4 color : COLOR; };
            V vert(A i)
            {
                V o;
                float3 pos = i.positionOS.xyz + i.normalOS * 0.015;
                o.p = TransformObjectToWorld(pos);
                o.positionCS = TransformWorldToHClip(o.p);
                o.n = TransformObjectToWorldNormal(i.normalOS);
                o.color = i.color;
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                half3 v = normalize(GetWorldSpaceViewDir(i.p));
                half f = pow(1.0h - saturate(dot(normalize(i.n), v)), 2.0h);
                half pulse = 0.75h + 0.25h * sin(_Time.y * 6.0h) * _Pulse;
                half3 base = lerp(FastSRGBToLinear(i.color.rgb), _BaseColor.rgb, 0.55h);
                half3 col = base * pulse + _BaseColor.rgb * f * 0.9h;
                return half4(col, saturate(_BaseColor.a + f * 0.4h));
            }
            ENDHLSL
        }
    }
}

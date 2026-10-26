# Male Manny Simple Ue5

Independent template (`male_manny_simple_ue5`) for the tested 88-bone `SKM_Manny_Simple` FBX skeleton, with a `root` armature object. Based on the bundled `male_mannequin_UE5` template; the original template is unchanged.

独立的简化 Manny 模板，适用于本次验证的 88 根肢体骨骼导出。完整 Manny 继续选择 **Male Mannequin Ue5**。

## Mapping changes / 映射改动

- Eight missing bilateral `upperarm/lowerarm/thigh/calf_correctiveRoot` links fall back to the corresponding main limb bones to drive the limb-origin Tweak controls.
- Existing Twist-to-intermediate-Tweak mappings are retained.
- Links to missing `clavicle_pec` bones and reverse links to absent corrective roots are omitted.
- Remapping nodes and sockets match the edited links. The original metarig is retained.

## Use / 使用

The full add-on installer includes this as a separate dropdown option on Blender 4+. The standalone `male_manny_simple_ue5.zip` is for **Import Template**, not Blender's **Install from Disk**. Only Blender 5.2.2 LTS was runtime-tested.

Ensure rest data and animated scale are consistently normalized to 1 before converting. Applying static object scale alone does not fix existing animated scale keys. Select the source armature in Source mode, choose **Male Manny Simple Ue5**, and click **Convert**. Reconvert the original animation if an older template already produced an incorrect bake.

完整插件更新后即可在下拉菜单中选择。转换前需统一绑定数据与动画缩放；以前已烘焙的错误关键帧需要重新转换，切换模板名称不会自动修正它们。

## Verification and limits / 验证范围与边界

Blender 5.2.2 LTS, supplied 282-frame sitting animation, 88 source bones and 438 generated Rigify bones. All 24 bilateral limb main/twist bones were compared on every frame: maximum position error **0.00038835 cm** (about **0.0039 mm**), measured rotation error **0 degrees**.

This template addresses limb Tweak misalignment caused by missing corrective roots. Existing approximate mappings remain. Across this clip, `ik_hand_gun` reaches about **6.47 cm** position difference and `neck_02` about **41.53 degrees** rotation difference; some finger bases also differ. It is not a lossless full-skeleton retargeter. Other Manny exports, scale conventions and animations require their own checks.

本模板的逐帧通过结论仅针对四肢主骨与 Twist；辅助骨、颈部及部分手指仍存在上述误差。它不是任意骨架通用、逐骨骼无损的自动重定向模板。

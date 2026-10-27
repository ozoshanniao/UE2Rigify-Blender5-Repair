# UE2Rigify Blender 5 Repair

将 Unreal Engine 角色骨架上的动画转换到 Rigify 控制器，在 Blender 中继续编辑，并可烘焙回源骨架。

Transfer Unreal Engine character animations to an editable Rigify control rig in Blender, then bake them back to the source skeleton.

**Version: 1.8.0 · Tested on Blender 5.2.2 LTS**

## 功能 / Features

- **UE → Rigify** — 生成 Rigify 控制骨架并转换源动画。Generate a Rigify control rig and transfer source animation.
- **Animation Scale** — 修复 UE 导出的恒定均匀缩放，保留世界空间运动和尺寸。Normalize constant uniform import scale while preserving world-space motion and size.
- **骨架模板 / Templates** — 内置 UE4/UE5 Mannequin、UEFN、MetaHuman 及独立的 **Male Manny Simple Ue5** 模板。
- **Bake** — 将编辑后的 Rigify 动画烘焙回源骨架。Bake edited Rigify animation back to the source skeleton.
- **映射编辑 / Remapping** — 使用节点编辑源骨架与 Rigify 之间的骨骼映射。Edit bone mappings through the node editor.

## 安装 / Installation

1. 下载 [插件安装包 1.8.0 / Download add-on ZIP](https://raw.githubusercontent.com/ozoshanniao/UE2Rigify-Blender5-Repair/main/dist/ue2rigify_1.8.0_blender5_repaired.zip)。
2. 在 Blender 首选项中使用 **Install from Disk** 安装 ZIP。Install the ZIP through Blender Preferences.
3. 启用 **Rigify** 和 **UE to Rigify (Blender 5 Repair)**。Enable both add-ons.

更新时替换旧版 UE to Rigify，重启 Blender 后重新启用插件。

When updating, replace the previous UE to Rigify installation and restart Blender.

## 使用 / Usage

1. 导入带动画的 UE FBX。Import an animated UE FBX.
2. 如需修复缩放，选中导入骨架，在 **UE to Rigify → Animation Scale** 中执行 **Check → Normalize Scale**。
   If scale normalization is needed, select the imported armature and run **Check → Normalize Scale** before conversion.
3. 在 **UE to Rigify Toolkit** 中选择 **Source** 骨架和匹配的 **Template**，将 Mode 设为 **Source**，点击 **Convert**。
   Select the source armature and matching template, set Mode to **Source**, and click **Convert**.
4. 使用生成的 Rigify 控制器编辑动画；需要回到原骨架时点击 **Bake**。
   Edit the animation with Rigify controls, then use **Bake** to transfer it back.

**Male Manny Simple Ue5** 用于简化 Manny 骨架；完整 Manny 使用 **Male Mannequin Ue5**。

Use **Male Manny Simple Ue5** for the simplified Manny skeleton and **Male Mannequin Ue5** for the full skeleton.

Animation Scale 需要 Blender **4.4+**，适用于恒定正数均匀缩放及单个活动 Action。转换前关闭 **Animation Auto Offset / Relative Editing**，避免位置编辑扩散到整段动画。

Animation Scale requires Blender **4.4+**, constant positive uniform scale, and one active Action. Disable **Animation Auto Offset / Relative Editing** before conversion to avoid propagating position changes across the animation.

## 来源与许可 / Credits & License

基于 [poly-hammer/BlenderTools](https://github.com/poly-hammer/BlenderTools)，原工具由 [Epic Games](https://github.com/EpicGames/BlenderTools) 开发；Animation Scale 来自 OZO_Tools。

Based on the projects above, with Animation Scale adapted from OZO_Tools. Distributed under [GPL-3.0-or-later](LICENSE.md), with the original upstream [MIT notice](LICENSE_UPSTREAM_MIT.md) retained.

# UE2Rigify Blender 5 Repair

UE to Rigify 的独立兼容性修复版，基于 **1.7.6**，在 **Blender 5.2.2 LTS** 验证。

This is an unofficial compatibility repair of UE to Rigify 1.7.6 for Blender 5. It is derived from the upstream project, not a new rigging system or an official release.

## 来源与致谢 / Upstream and attribution

- 直接来源 / Based on: [poly-hammer/BlenderTools](https://github.com/poly-hammer/BlenderTools), UE to Rigify 1.7.6.
- 原始项目与作者 / Original project and author: [EpicGames/BlenderTools](https://github.com/EpicGames/BlenderTools), Epic Games, Inc.
- 原项目文档 / Upstream documentation: [UE to Rigify](https://poly-hammer.github.io/BlenderTools/ue2rigify/).
- 原插件的代码、模板、资源及版权声明均予以保留。本仓库主要提供 Blender 5 动画接口兼容与相关烘焙修复。
- Original code, templates, resources, and copyright notices are retained. This repository is independently maintained and is not endorsed by Epic Games or Poly Hammer.

Upstream uses the **MIT License**; its full notice is preserved in [LICENSE_UPSTREAM_MIT.md](LICENSE_UPSTREAM_MIT.md) and inside the add-on. Version **1.8.0** also incorporates OZO's **GPL-3.0-or-later** Animation Scale module. The combined 1.8.0 add-on is distributed under GPL-3.0-or-later; see [LICENSE.md](LICENSE.md) and [OZO attribution](ue2rigify/OZO_ANIMATION_SCALE_NOTICE.md). Original upstream MIT notices and permissions remain intact. Earlier 1.7.x archives and the standalone template ZIP are unchanged.

## 下载与安装 / Install

1. 下载 [完整安装 ZIP（1.8.0）](dist/ue2rigify_1.8.0_blender5_repaired.zip)，在 GitHub 文件页面点击下载原始文件。
2. 在 Blender 首选项中禁用旧版 UE to Rigify，通过“从磁盘安装”选择此 ZIP，替换旧版后重启 Blender。
3. 启用 **Rigify** 与 **UE to Rigify (Blender 5 Repair)**。

Download the ZIP above using GitHub's raw-file download button, then install it through Blender's **Install from Disk**. The repository's **Code → Download ZIP** archive is a source archive, not the Blender installer.

版本标识为 **1.8.0（1.8）**，仅用于区分本地修复版，并非官方上游版本。模块名仍为 `ue2rigify`，因此原版与修复版应替换安装，不能同时启用。

The local repair identifies itself as version **1.8.0** and keeps the `ue2rigify` module name for saved-file compatibility. Install it as a replacement for the original add-on.

## 1.8：OZO Animation Scale / UE import scale normalization

将 OZO_Tools 0.5.2 的 **Animation Scale** 功能移植到 **UE to Rigify → Animation Scale**。原 OZO 插件保持不变，两个工具可以同时启用；新工具无需依赖 OZO 安装。

1. 在 Object/Pose 模式选中**原始导入的骨架对象**，在 Convert 之前运行。
2. 打开 **Animation Scale**，确认 **Active** 显示的是要修复的骨架。
3. 点击 **Check** 检查，再点 **Normalize Scale**。
4. 通过后再选择对应模板并执行 **Convert**。

它会复制骨架数据、子网格和 Action，将恒定、正数、XYZ 一致的物体缩放归一为 1，同时修正骨骼位移动画与关键帧手柄。工具逐帧比较世界空间骨骼端点和全部求值网格顶点，验证失败会回滚；原 Action 保留，工具不保存 blend 文件。它不改变动画时长，也不是角色身高匹配工具。

The port preserves OZO's copy/verify/rollback workflow, with independent UE2Rigify operators and scene settings. It normalizes the **active imported armature** and supported direct child meshes before conversion. It is not applied automatically by Convert. The original Action is retained, and an already normalized input is a no-op.

适用范围保持与 OZO 原工具一致：单个活动 Action、单个动作槽、单层和单个 keyframe strip。NLA、约束/驱动、变化或非均匀缩放、Shape Keys、共享/链接数据及不支持的网格变换会显示具体原因，不会强行处理。世界空间验证容差为 `2e-5` Blender 单位，基线数据上限为 512 MiB。

Animation Scale requires Blender **4.4+**; it was runtime-tested on **5.2.2 LTS**. Existing older-Blender retargeting paths remain separate. See [OZO module notes](ue2rigify/OZO_ANIMATION_SCALE_NOTICE.md) and [regression results](tests/animation_scale_validation_results.json).

实际 UE FBX 验证覆盖 88 根骨骼、48,705 个网格顶点和 282 帧，骨骼/顶点最大世界空间偏差分别约 `8.52e-6` / `8.19e-6` Blender 单位，均低于容差；随后使用 Manny Simple 模板完成 Rigify 转换。记录见 [原始 FBX 缩放检查](tests/animation_scale_fbx_results.json) 与 [1.8 完整流程](tests/manny_simple_1_8_validation_results.json)。

## 1.7.8：独立 Manny Simple 模板 / Separate Manny Simple template

新增 **Male Manny Simple Ue5**，模板标识为 `male_manny_simple_ue5`。它是独立选项，不修改原有 **Male Mannequin Ue5**。完整安装包已内置该模板，更新并重新启用插件后会复制到模板目录，无需单独导入。

此模板适用于本次验证的 `SKM_Manny_Simple` 骨架：88 根肢体骨骼，以及 `root` 骨架对象；缺少 8 根双侧四肢 `correctiveRoot` 和 2 根 `clavicle_pec`。新模板用对应主骨骼驱动四肢起点 Tweak，保留 Twist 到中间 Tweak 的映射，并移除不存在骨骼的映射及节点插槽。

**Male Manny Simple Ue5** is a separate Blender 4+ template for the tested simplified Manny skeleton. The full **Male Mannequin Ue5** template is unchanged. Eight missing corrective-root links fall back to their main limb bones; existing twist mappings are preserved. Links to absent pectoral/corrective bones are omitted. Tested on Blender 5.2.2 LTS with a 282-frame sitting animation; this does not establish compatibility with every Manny export or older Blender versions.

已有修复版用户也可下载 [独立模板 ZIP](dist/male_manny_simple_ue5.zip)，通过插件设置中的 **Import Template** 导入。该 ZIP 是模板，不是可安装的 Blender 插件。转换前需确保源骨架的绑定数据与动画缩放均已统一为 1；仅对物体执行 Apply Scale 不会自动修正已有的缩放关键帧。

If you already have the repair add-on, use **Import Template** with the standalone template ZIP. For full Manny skeletons, keep using the original template. Normalize both rest-data and animated scale before conversion. Reconvert the original animation to replace an earlier incorrect bake; simply changing the selected template will not repair existing baked keys.

逐帧验证范围为 24 根四肢主骨和 Twist 骨骼，覆盖全部 282 帧。原模板对辅助 `ik_hand_gun`、部分手指根节和颈部仍有近似映射，**不宣称全骨架无损一致**。详见 [模板说明](ue2rigify/resources/rig_templates/b4_0/male_manny_simple_ue5/README.md) 和 [验证记录](tests/manny_simple_validation_results.json)。

## 修复内容 / Changes

- 适配 Blender 4.4+ / 5.x 的 Action 层、动作槽、关键帧 strip 与 channelbag，修复 `Action.fcurves` 被移除后的错误。
- 显式绑定活动 Action 与 NLA strip 的动作槽；读取、偏移和删除曲线时限定到当前对象的动作槽。
- 适配 Blender 5 的 `PoseBone.select`，同时保留旧版本选择接口。
- 转换时只烘焙映射的 Rigify 控制骨，避免将内部机制骨与变形骨一并写入关键帧导致根运动重复。

The repair supports slotted Action curve access and assignment, updates pose-bone selection, and avoids baking generated Rigify internals alongside controls. See [REPAIR_NOTES.md](ue2rigify/REPAIR_NOTES.md) for technical details.

## 已验证的工作流 / Verified workflow

使用 Blender **5.2.2 LTS**、90 根源骨骼的 UEFN mannequin、**1–77 帧**动画：

1. Source 骨架选择 `root`，模板选择 **Uefn Mannequin**。
2. Mode 切为 **Source**，点击 **Convert**。
3. 成功生成 438 根骨骼的 Rigify，动画在控制骨架上播放。

全部映射控制骨烘焙、按关键帧映射烘焙、活动与 NLA 动作槽绑定及多动作槽隔离均已测试。骨盆、头、左手与左脚在全部 77 帧中的世界位置最大偏差约为 **0.0000021 Blender units**。回烘全部源骨可运行，相同采样的最大偏差约为 **0.0033 Blender units**，并非无损往返。

Recorded reports: [full conversion](tests/validation_results.json), [sparse conversion](tests/validation_sparse_results.json). These reports describe the supplied UEFN test scene. Manny Simple has a separate report above. Older Blender compatibility paths are retained but were not runtime-tested. Other templates were not runtime-tested. The user's model and animation files are not included in this repository.

## 开发 / Development

完整插件源码位于 `ue2rigify/`。在仓库根目录运行以下命令，可执行不依赖外部模型的 Blender 5 动作槽回归检查：

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_action_slots.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_animation_scale.py
```

The regression script checks shared-Action slot isolation and NLA slot ownership. It does not replace the scene-based retargeting validation above.

Verify template/node consistency and packaged resources without Blender:

```sh
python tests/test_manny_simple_template.py
```

Optional integration test with your own Manny Simple FBX (the test normalizes FBX scale in its disposable background scene):

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_manny_simple_conversion.py -- --fbx /path/to/anim_Sitting_Down_01.FBX
```

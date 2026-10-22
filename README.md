# UE2Rigify Blender 5 Repair

UE to Rigify 的独立兼容性修复版，基于 **1.7.6**，在 **Blender 5.2.2 LTS** 验证。

This is an unofficial compatibility repair of UE to Rigify 1.7.6 for Blender 5. It is derived from the upstream project, not a new rigging system or an official release.

## 来源与致谢 / Upstream and attribution

- 直接来源 / Based on: [poly-hammer/BlenderTools](https://github.com/poly-hammer/BlenderTools), UE to Rigify 1.7.6.
- 原始项目与作者 / Original project and author: [EpicGames/BlenderTools](https://github.com/EpicGames/BlenderTools), Epic Games, Inc.
- 原项目文档 / Upstream documentation: [UE to Rigify](https://poly-hammer.github.io/BlenderTools/ue2rigify/).
- 原插件的代码、模板、资源及版权声明均予以保留。本仓库主要提供 Blender 5 动画接口兼容与相关烘焙修复。
- Original code, templates, resources, and copyright notices are retained. This repository is independently maintained and is not endorsed by Epic Games or Poly Hammer.

Upstream uses the **MIT License**. Its full notice is preserved in [LICENSE.md](LICENSE.md), and inside the installable add-on.

## 下载与安装 / Install

1. 下载 [完整安装 ZIP](dist/ue2rigify_1.7.7_blender5_repaired.zip)，在 GitHub 文件页面点击下载原始文件。
2. 在 Blender 首选项中禁用旧版 UE to Rigify，通过“从磁盘安装”选择此 ZIP，替换旧版后重启 Blender。
3. 启用 **Rigify** 与 **UE to Rigify (Blender 5 Repair)**。

Download the ZIP above using GitHub's raw-file download button, then install it through Blender's **Install from Disk**. The repository's **Code → Download ZIP** archive is a source archive, not the Blender installer.

版本标识为 **1.7.7**，仅用于区分本地修复版，并非官方上游版本。模块名仍为 `ue2rigify`，因此原版与修复版应替换安装，不能同时启用。

The local repair identifies itself as version **1.7.7** and keeps the `ue2rigify` module name for saved-file compatibility. Install it as a replacement for the original add-on.

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

Recorded reports: [full conversion](tests/validation_results.json), [sparse conversion](tests/validation_sparse_results.json). These reports describe the supplied UEFN test scene, not every character or template. Older Blender compatibility paths are retained but were not runtime-tested. Other templates were not runtime-tested. The user's model and animation files are not included in this repository.

## 开发 / Development

完整插件源码位于 `ue2rigify/`。在仓库根目录运行以下命令，可执行不依赖外部模型的 Blender 5 动作槽回归检查：

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_action_slots.py
```

The regression script checks shared-Action slot isolation and NLA slot ownership. It does not replace the scene-based retargeting validation above.

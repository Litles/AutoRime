# AutoRime
Rime 打字模拟和数据统计

## 使用方法

1. 将需要测试的某方案的相关文件（`dict.yaml`、`schema.yaml`等）拷贝到 Rime 文件夹内；
2. （重要）将准备的`mapping_table.txt`文件拷贝到`auto_rime`文件夹（覆盖默认的文件）；
3. 将该方案设为首选方案：编辑`default.custom.yaml`，取消`- {schema: myschema}`那行的注释（将`myschema`改为实际方案的名称）；
4. 部署该方案：双击执行`build.bat`；
5. （重要）测试该方案是否部署成功且有效：双击执行`test.bat`，输入编码会返回候选，并显示当前输入法状态（确认是你的输入法，而不默认的“拼音简体”），输入`1`可以上屏首选，输入`exit`可退出；
6. 上一步确认没问题后，就可以开始进行打字模拟了：双击运行`AutoRime.exe`即可。

### 补充说明

+ `auto_rime`文件夹内的所有文本文件一律要求是 UTF-8 无签名格式；
+ `mapping_table.txt`文件的格式类似于单字码表，规定了模拟跟打程序碰到相应的字时，应该对应输入什么编码。因此要求一字一码，暂不支持一字多码。

## 参考

+ https://github.com/rime/librime

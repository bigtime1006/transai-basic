| 模型名称                                   | 限流条件（超出任一数值时触发限流）                           |                  |
|----------------------------------------|---------------------------------------------|------------------|
|                                        | 以下为每分钟限流条件，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制 |                  |
|                                        | 每分钟调用次数（RPM）                                | 每分钟消耗Token数（TPM） |
|                                        |                                             | 含输入与输出Token      |
| qwen-plus(用Batch API调用服务时，不受限流限制。)     | 15,000                                      | 1,200,000        |
| qwen-mt-plus                           | 60                                          | 23,797           |
| qwen-mt-turbo                          |                                             | 31,980           |
| *以上参数是开发测试时的限制,上生产时可以与阿里云协商,进行限制条件的扩展. |                                             |                  |

为了保证用户调用模型的公平性，阿里云百炼设置了基础限流。限流基于模型维度且与用户的阿里云主账号相关联，按照该账号下所有API-KEY调用该模型的总和计算限流。若超出限制，API请求将会失败，需等到解除限流条件时再次调用。

限流规则
主账号维度：按主账号下，所有子账号、所有业务空间、所有API-KEY的调用总和计算。

不同模型独立限流：具体参见下方表格。

限流FAQ
为什么触发限流？
根据错误信息判断

Requests rate limit exceeded或You exceeded your current requests list：表示调用频率触发限流。

Allocated quota exceeded或You exceeded your current quota：表示Token消耗触发限流。

其他报错请参考错误信息确认原因。

按秒限制：除了RPM（Requests Per Minute，每分钟请求数）和TPM，服务可能按 RPS（RPM/60）与 TPS（TPM/60）限制。

如需查看监控，可通过模型观测页面查看调用统计。需注意该页面数据延迟1-2小时。
遇到限流后多久恢复？
通常在一分钟内恢复。若出现其他报错，请根据错误信息进行解决。

如何避免限流？
选用高限流模型

优先使用 qwen-plus 等限流宽松的模型。

稳定版或最新版比带日期的快照版本限流更宽松。

优化调用策略

调整调用频率：触发Requests rate limit exceeded或You exceeded your current requests list时，降低调用频率。

减少Token消耗：触发Allocated quota exceeded或You exceeded your current quota时，缩短输入或输出长度。

添加备选模型

建议您在遇到限流报错后切换到备用模型继续生成，提升并发并降低失败概率。以下代码展示了调用 qwen-plus-2025-07-28 触发限流，改用 qwen-plus-2025-07-14 重发请求的示例。

示例代码

任务拆分：将大批量任务拆分为小批次，在不同时间段提交。

批量推理：如果无需实时返回结果，可使用批量推理（Batch API），不受实时限流约束，但需考虑排队和处理时间。

https://bailian.console.aliyun.com/?spm=5176.smartservice_service_robot_chat_new.0.0.4c803a98KON7j2&tab=api&scm=20140722.M_10838628._.V_1#/api/?type=model&url=2842025&userCode=okjhlpr5
OpenAI兼容-Batch
阿里云百炼提供与OpenAI兼容的Batch接口，支持以文件方式批量提交任务并异步执行，在非高峰时段离线处理大规模数据，任务完成或达到最长等待时间时返回结果，费用仅为实时调用的50%。

如需在控制台操作，请参见批量推理。
前提条件
已开通阿里云百炼服务，并已获取API Key：获取API Key。

建议您配置API Key到环境变量中以降低API Key的泄露风险。
如果您使用OpenAI Python SDK调用Batch接口，请通过以下命令安装最新版OpenAI SDK。

 
pip3 install -U openai
支持的模型
文本生成模型

通义千问 Max：qwen-max、qwen-max-latest

通义千问 Plus：qwen-plus、qwen-plus-latest

通义千问 Flash：qwen-flash

通义千问 Turbo：qwen-turbo、qwen-turbo-latest

通义千问 Long：qwen-long、qwen-long-latest

QwQ：qwq-plus

QwQ-Preview：qwq-32b-preview

多模态模型

视觉理解（Qwen-VL）：qwen-vl-max、qwen-vl-max-latest、qwen-vl-plus、qwen-vl-plus-latest

文字提取（Qwen-OCR）：qwen-vl-ocr

全模态：qwen-omni-turbo

文本向量模型：text-embedding-v1、text-embedding-v2、text-embedding-v3、text-embedding-v4

第三方模型：deepseek-r1、deepseek-v3

计费
Batch调用的费用为实时调用的50%，具体请参见模型列表。

Batch推理不支持以下服务或优惠：预付费（节省计划）、免费额度、Context Cache等。

快速开始
在正式Batch任务开始之前，您可使用测试模型batch-test-model进行全链路闭环测试，包括验证输入数据、创建任务、查询任务及下载结果文件等流程。请注意：

测试文件不仅需满足输入文件格式要求，还需满足单文件大小不超过1MB，且文件行数不超过100行的要求；

并发限制：最大并行任务数2个；

资源使用：测试模型不走推理流程，因此不产生模型推理费用。

具体步骤如下：

准备测试文件

将包含请求信息的示例文件test_model.jsonl下载到本地，并确保其与下方的Python脚本置于同一目录下。

示例内容：model参数设置为batch-test-model，url设置为/v1/chat/ds-test 。

 
{"custom_id":"1","method":"POST","url":"/v1/chat/ds-test","body":{"model":"batch-test-model","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/ds-test","body":{"model":"batch-test-model","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
运行脚本

执行此Python脚本。

如果需要调整文件路径或其他参数，请根据实际情况修改代码。
 
import os
from pathlib import Path
from openai import OpenAI
import time

# 初始化客户端
client = OpenAI(
    # 若没有配置环境变量,可用阿里云百炼API Key将下行替换为：api_key="sk-xxx",但不建议在生产环境中直接将API Key硬编码到代码中,以减少API Key泄露风险.
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 阿里云百炼服务的base_url
)

def upload_file(file_path):
    print(f"正在上传包含请求信息的JSONL文件...")
    file_object = client.files.create(file=Path(file_path), purpose="batch")
    print(f"文件上传成功。得到文件ID: {file_object.id}\n")
    return file_object.id

def create_batch_job(input_file_id):
    print(f"正在基于文件ID，创建Batch任务...")
    # 请注意:此处endpoint参数值需和输入文件中的url字段保持一致.测试模型(batch-test-model)填写/v1/chat/ds-test,Embedding文本向量模型填写/v1/embeddings,其他模型填写/v1/chat/completions
    batch = client.batches.create(input_file_id=input_file_id, endpoint="/v1/chat/ds-test", completion_window="24h")
    print(f"Batch任务创建完成。 得到Batch任务ID: {batch.id}\n")
    return batch.id

def check_job_status(batch_id):
    print(f"正在检查Batch任务状态...")
    batch = client.batches.retrieve(batch_id=batch_id)
    print(f"Batch任务状态: {batch.status}\n")
    return batch.status

def get_output_id(batch_id):
    print(f"正在获取Batch任务中执行成功请求的输出文件ID...")
    batch = client.batches.retrieve(batch_id=batch_id)
    print(f"输出文件ID: {batch.output_file_id}\n")
    return batch.output_file_id

def get_error_id(batch_id):
    print(f"正在获取Batch任务中执行错误请求的输出文件ID...")
    batch = client.batches.retrieve(batch_id=batch_id)
    print(f"错误文件ID: {batch.error_file_id}\n")
    return batch.error_file_id

def download_results(output_file_id, output_file_path):
    print(f"正在打印并下载Batch任务的请求成功结果...")
    content = client.files.content(output_file_id)
    # 打印部分内容以供测试
    print(f"打印请求成功结果的前1000个字符内容: {content.text[:1000]}...\n")
    # 保存结果文件至本地
    content.write_to_file(output_file_path)
    print(f"完整的输出结果已保存至本地输出文件result.jsonl\n")

def download_errors(error_file_id, error_file_path):
    print(f"正在打印并下载Batch任务的请求失败信息...")
    content = client.files.content(error_file_id)
    # 打印部分内容以供测试
    print(f"打印请求失败信息的前1000个字符内容: {content.text[:1000]}...\n")
    # 保存错误信息文件至本地
    content.write_to_file(error_file_path)
    print(f"完整的请求失败信息已保存至本地错误文件error.jsonl\n")

def main():
    # 文件路径
    input_file_path = "test_model.jsonl"  # 可替换为您的输入文件路径
    output_file_path = "result.jsonl"  # 可替换为您的输出文件路径
    error_file_path = "error.jsonl"  # 可替换为您的错误文件路径
    try:
        # Step 1: 上传包含请求信息的JSONL文件,得到输入文件ID,如果您需要输入OSS文件,可将下行替换为：input_file_id = "实际的OSS文件URL或资源标识符"
        input_file_id = upload_file(input_file_path)
        # Step 2: 基于输入文件ID,创建Batch任务
        batch_id = create_batch_job(input_file_id)
        # Step 3: 检查Batch任务状态直到结束
        status = ""
        while status not in ["completed", "failed", "expired", "cancelled"]:
            status = check_job_status(batch_id)
            print(f"等待任务完成...")
            time.sleep(10)  # 等待10秒后再次查询状态
        # 如果任务失败,则打印错误信息并退出
        if status == "failed":
            batch = client.batches.retrieve(batch_id)
            print(f"Batch任务失败。错误信息为:{batch.errors}\n")
            print(f"参见错误码文档: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
            return
        # Step 4: 下载结果：如果输出文件ID不为空,则打印请求成功结果的前1000个字符内容，并下载完整的请求成功结果到本地输出文件;
        # 如果错误文件ID不为空,则打印请求失败信息的前1000个字符内容,并下载完整的请求失败信息到本地错误文件.
        output_file_id = get_output_id(batch_id)
        if output_file_id:
            download_results(output_file_id, output_file_path)
        error_file_id = get_error_id(batch_id)
        if error_file_id:
            download_errors(error_file_id, error_file_path)
            print(f"参见错误码文档: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"参见错误码文档: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")

if __name__ == "__main__":
    main()
验证测试结果

任务状态显示completed。

结果文件result.jsonl：包含固定响应{"content":"This is a test result."}。

 
{"id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","custom_id":"1","response":{"status_code":200,"request_id":"a2b1ae25-21f4-4d9a-8634-99a29926486c","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-bca7295b-67c3-4b1f-8239-d78323bb669f","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
{"id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","custom_id":"2","response":{"status_code":200,"request_id":"39b74f09-a902-434f-b9ea-2aaaeebc59e0","body":{"created":1743562621,"usage":{"completion_tokens":6,"prompt_tokens":20,"total_tokens":26},"model":"batch-test-model","id":"chatcmpl-1e32a8ba-2b69-4dc4-be42-e2897eac9e84","choices":[{"finish_reason":"stop","index":0,"message":{"content":"This is a test result."}}],"object":"chat.completion"}},"error":null}
如遇到错误，请参考错误信息进行解决。
通过测试验证后，您可以通过以下步骤来执行正式的Batch任务流程。

参考输入文件格式要求准备输入文件，并将文件中的model参数设置为支持的模型，url设置为：

Embedding文本向量模型填写/v1/embeddings；

其他模型填写/v1/chat/completions。

替换上面Python脚本中的endpoint；

重要
请确保脚本中的endpoint与输入文件中的url参数保持一致。

运行脚本，等待任务完成，若任务成功，将在同一目录下生成输出结果文件result.jsonl。

若任务失败，则程序退出并打印错误信息。
如果存在错误文件ID，将在同一目录下生成错误文件error.jsonl以供检查。
在过程中发生的异常会被捕获，并打印错误信息。
数据文件格式说明
输入文件格式
Batch任务的输入文件为 JSONL 文件，格式要求如下：

每行一个 JSON 格式的请求。

单个 Batch 任务最多包含 50,000 个请求。

单个 Batch 任务的所有请求都必须选用同一个模型。

Batch 文件最大500 MB。

文件中单行最大 6 MB。

单行的请求内容需遵循各模型上下文长度的限制。

请求示例
您可通过下方工具选择模型，以查看对应的jsonl请求示例，可将其复制到您的输入文件中。

选择模型系列:

文本生成模型
选择模型:

qwen-max
 
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-max","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-max","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
重要
在创建Batch任务的接口中，endpoint参数值必须和请求示例中的url字段保持一致；

同一任务的批量请求务必选择同一模型。

请求参数




字段

类型

必选

描述

custom_id

String

是

用户自定义的请求ID，每一行表示一条请求，每一条请求有一个唯一的 custom_id。Batch任务结束后，可以在结果文件中找到该 custom_id 对应的请求结果。

method

String

是

请求方法，当前只支持POST。

url

String

是

API关联的URL，需和创建Batch任务时的endpoint字段保持一致。

Embedding文本向量模型填写/v1/embeddings；

测试模型batch-test-model填写/v1/chat/ds-test；

其他模型填写/v1/chat/completions。

body

Object

是

模型调用的请求体，包含调用模型所需的全部参数，如model、messages、enable_thinking，thinking_budget等。

请求体中的参数与实时推理接口所支持的参数保持一致。更多参数详情请参考 OpenAI兼容API。

如果您需要进一步扩展，比如支持更多参数（如max_tokens, temperature等），也可以添加到 body 中，参数之间通过英文逗号隔开。

示例：

 
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-turbo-latest","stream":true,"enable_thinking":true,"thinking_budget":50,"messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你是谁？"}],"max_tokens": 1000,"temperature":0.7}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-turbo-latest","stream":true,"enable_thinking":true,"thinking_budget":50,"messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}],"max_tokens": 1000,"temperature":0.7}}
body.model

String

是

本次Batch任务使用的模型。

重要
同一任务的批量请求务必选择同一模型。

body.messages

Array

是

消息列表。

 
[
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "What is 2+2?"}
]
body.enable_thinking

Boolean

否

表示是否开启深度思考。默认为false。

设置enable_thinking 为 true，qwen-plus，qwen-flash，qwen-turbo，qwen-plus-latest、qwen-turbo-latest将开启推理模式，模型会先输出思考过程，再输出回答内容，思考过程在reasoning_content字段输出。

重要
该参数对 qwq-plus 与 deepseek-r1 模型无效。

body.thinking_budget

Integer

否

思考过程最大 Token 数。

thinking_budget的设置不会影响大模型的思考过程。如果模型思考过程生成的 Token 数超过thinking_budget，推理内容会进行截断并立刻开始生成最终回复内容。

重要
该参数对qwq-plus 与 deepseek-r1 模型无效。

CSV文件转换为JSONL文件
如果您有一份第一列为请求id（custom_id）第二列为内容（content）的 CSV 文件，您可以通过下方Python代码快速创建一份符合Batch任务格式的JSONL文件。此特定格式的 CSV 文件应与下方的Python脚本放置在同一目录中。

也可以使用本文提供的模板文件，具体步骤如下：

将模板文件下载到本地，并与下方的Python脚本置于同一目录下；

这里的CSV模板文件格式是第一列为请求id（custom_id），第二列为内容（content），您可以将您的业务问题粘贴到这个文件中。

运行下方 Python 脚本代码后，将在同一目录下生成一个符合Batch任务文件格式的名为input_demo.jsonl的JSONL文件。

如果需要调整文件路径或其他参数，请根据实际情况修改代码。
 
import csv
import json
def messages_builder_example(content):
    messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": content}]
    return messages

with open("input_demo.csv", "r") as fin:
    with open("input_demo.jsonl", 'w', encoding='utf-8') as fout:
        csvreader = csv.reader(fin)
        for row in csvreader:
            body = {"model": "qwen-turbo", "messages": messages_builder_example(row[1])}
            # 选择Embedding文本向量模型进行调用时，url的值需填写"/v1/embeddings",其他模型填写/v1/chat/completions
            request = {"custom_id": row[0], "method": "POST", "url": "/v1/chat/completions", "body": body}
            fout.write(json.dumps(request, separators=(',', ':'), ensure_ascii=False) + "\n", )
输出文件格式
JSONL文件，每行一个JSON，对应一个请求结果。

返回示例
一个单行内容示例：

 
{"id":"73291560-xxx","custom_id":"1","response":{"status_code":200,"request_id":"73291560-7616-97bf-87f2-7d747bbe84fd","body":{"created":1742303743,"usage":{"completion_tokens":7,"prompt_tokens":26,"total_tokens":33},"model":"qwen-max","id":"chatcmpl-73291560-7616-97bf-87f2-7d747bbe84fd","choices":[{"finish_reason":"stop","index":0,"message":{"content":"2+2 equals 4."}}],"object":"chat.completion"}},"error":null}
一个多行内容示例：

 
{"id":"c308ef7f-xxx","custom_id":"1","response":{"status_code":200,"request_id":"c308ef7f-0824-9c46-96eb-73566f062426","body":{"created":1742303743,"usage":{"completion_tokens":35,"prompt_tokens":26,"total_tokens":61},"model":"qwen-max","id":"chatcmpl-c308ef7f-0824-9c46-96eb-73566f062426","choices":[{"finish_reason":"stop","index":0,"message":{"content":"你好！当然可以。无论是需要信息查询、学习资料、解决问题的方法，还是其他任何帮助，我都在这里为你提供支持。请告诉我你需要什么方面的帮助？"}}],"object":"chat.completion"}},"error":null}
{"id":"73291560-xxx","custom_id":"2","response":{"status_code":200,"request_id":"73291560-7616-97bf-87f2-7d747bbe84fd","body":{"created":1742303743,"usage":{"completion_tokens":7,"prompt_tokens":26,"total_tokens":33},"model":"qwen-max","id":"chatcmpl-73291560-7616-97bf-87f2-7d747bbe84fd","choices":[{"finish_reason":"stop","index":0,"message":{"content":"2+2 equals 4."}}],"object":"chat.completion"}},"error":null}
深度思考模型，返回示例：

 
{"id":"6bcfa649-ac02-9de6-836c-f2fdefe8c4ae","custom_id":"1","response":{"status_code":200,"request_id":"6bcfa649-ac02-9de6-836c-f2fdefe8c4ae","body":{"created":1747103521,"usage":{"completion_tokens":106,"prompt_tokens":22,"completion_tokens_details":{"reasoning_tokens":50},"total_tokens":128},"model":"qwen-turbo-latest","id":"chatcmpl-6bcfa649-ac02-9de6-836c-f2fdefe8c4ae","choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"我是通义千问，是阿里巴巴集团旗下的通义实验室研发的超大规模语言模型。我能够回答问题、创作文字、逻辑推理、编程等多种任务。你可以叫我Qwen或者通义千问。有什么我可以帮你的吗？","reasoning_content":"好的，用户问“你是谁？”，我需要给出一个准确且友好的回答。首先，我应该明确自己的身份，即通义千问，由阿里巴巴集团旗下的通义实验室研发。接下来，要说明我的主要功能，"}}],"object":"chat.completion"}},"error":null}
{"id":"d4117b6f-efcf-90e7-b2ee-a064264d4619","custom_id":"2","response":{"status_code":200,"request_id":"d4117b6f-efcf-90e7-b2ee-a064264d4619","body":{"created":1747103521,"usage":{"completion_tokens":63,"prompt_tokens":26,"completion_tokens_details":{"reasoning_tokens":50},"total_tokens":89},"model":"qwen-turbo-latest","id":"chatcmpl-d4117b6f-efcf-90e7-b2ee-a064264d4619","choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"2 + 2 equals 4.","reasoning_content":"Okay, the user is asking \"What is 2+2?\" That's a straightforward arithmetic question. Let me think about how to approach this.\n\nFirst, I know that 2 plus 2 is a basic math problem. In standard arithmetic,"}}],"object":"chat.completion"}},"error":null}
返回参数




字段

类型

必选

描述

id

String

是

请求ID。

custom_id

String

是

用户自定义的请求ID。

response

Object

否

请求结果。

error

Object

否

异常响应结果。

error.code

String

否

错误码。

error.message

String

否

错误信息。

completion_tokens

Integer

否

完成生成所需的token数。

prompt_tokens

Integer

否

prompt的token数。

reasoning_tokens

Integer

否

深度思考模型的思考过程token数。

model

String

否

本次任务进行推理的模型。

reasoning_content

String

否

深度思考模型的思考过程。

JSONL文件转换为CSV文件
相比于JSONL文件，CSV文件通常只包含必要的数据值，没有额外的键名或其他元数据，非常适合用于自动化脚本和Batch任务。如果您需要将Batch输出的 JSONL 文件转换成 CSV 文件，可以使用以下Python代码实现。

请确保将 result.jsonl 文件与下方的 Python 脚本放在同一目录下，运行下方脚本代码后会生成一个名为 result.csv 的 CSV 文件。

如果需要调整文件路径或其他参数，请根据实际情况修改代码。
 
import json
import csv
columns = ["custom_id",
           "model",
           "request_id",
           "status_code",
           "error_code",
           "error_message",
           "created",
           "content",
           "usage"]

def dict_get_string(dict_obj, path):
    obj = dict_obj
    try:
        for element in path:
            obj = obj[element]
        return obj
    except:
        return None

with open("result.jsonl", "r") as fin:
    with open("result.csv", 'w', encoding='utf-8') as fout:
        rows = [columns]
        for line in fin:
            request_result = json.loads(line)
            row = [dict_get_string(request_result, ["custom_id"]),
                   dict_get_string(request_result, ["response", "body", "model"]),
                   dict_get_string(request_result, ["response", "request_id"]),
                   dict_get_string(request_result, ["response", "status_code"]),
                   dict_get_string(request_result, ["error", "error_code"]),
                   dict_get_string(request_result, ["error", "error_message"]),
                   dict_get_string(request_result, ["response", "body", "created"]),
                   dict_get_string(request_result, ["response", "body", "choices", 0, "message", "content"]),
                   dict_get_string(request_result, ["response", "body", "usage"])]
            rows.append(row)
        writer = csv.writer(fout)
        writer.writerows(rows)
当CSV文件中包含中文字符，并且使用Excel打开时遇到乱码问题时，可以使用文本编辑器（如Sublime）将CSV文件的编码转换为GBK，然后再用Excel打开。另一种方法是在Excel中新建一个Excel文件，并在导入数据时指定正确的编码格式UTF-8。
具体流程
1. 准备与上传文件
如果您需要使用OSS文件创建Batch任务，可跳过此步骤。
创建Batch任务前，需要您将准备好的符合输入文件格式要求的JSONL文件，通过以下的文件上传接口上传后，获取file_id，通过purpose参数指定上传文件的用途为batch。

您可以上传Batch任务的单个文件最大为500 MB；当前阿里云账号下的百炼存储空间支持的最大文件数为10000个，文件总量不超过100 GB，文件暂时没有有效期。当您的文件空间达到限制后，可以通过删除文件接口删除不需要的文件以释放空间。

OpenAI Python SDKcurl
请求示例
 
import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼服务的base_url
)

# test.jsonl 是一个本地示例文件，purpose必须是batch
file_object = client.files.create(file=Path("test.jsonl"), purpose="batch")

print(file_object.model_dump_json())
测试文件test.jsonl内容：

 
{"custom_id":"1","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"你好！有什么可以帮助你的吗？"}]}}
{"custom_id":"2","method":"POST","url":"/v1/chat/completions","body":{"model":"qwen-plus","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"What is 2+2?"}]}}
返回示例
 
{
    "id": "file-batch-xxx",
    "bytes": 437,
    "created_at": 1742304153,
    "filename": "test.jsonl",
    "object": "file",
    "purpose": "batch",
    "status": "processed",
    "status_details": null
}
2. 创建Batch任务
您可以通过两种方式使用input_file_id参数创建Batch任务：一是传入准备与上传文件接口返回的文件ID；二是传入OSS文件URL或资源标识符。第二种方式无需调用上传文件接口，避免上传文件的数量和总容量限制。

接口限流：每个阿里云主账号每分钟1000次，最大运行任务数1000个（包括所有未结束的任务，超过最大任务数，需要等任务结束后才能再创建）。

OpenAI Python SDKcurl
请求示例
 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼服务的base_url
)

batch = client.batches.create(
    input_file_id="file-batch-xxx",  # 上传文件返回的id或OSS文件URL或OSS文件资源标识符
    endpoint="/v1/chat/completions",  # Embedding文本向量模型填写/v1/embeddings,测试模型batch-test-model填写/v1/chat/ds-test,其他模型填写/v1/chat/completions
    completion_window="24h",
    metadata={'ds_name':"任务名称",'ds_description':'任务描述'} # metadata数据，非必填字段，用于创建任务名称、描述
)
print(batch)
输入参数配置





字段

类型

传参方式

必选

描述

input_file_id

String

Body

是

用于指定文件ID、OSS文件URL或OSS文件资源标识符，作为Batch任务的输入文件。您可以通过以下任一方式提供此参数：

准备与上传文件接口返回的文件ID，如file-batch-xxx；

使用OSS文件创建Batch任务。

endpoint

String

Body

是

访问路径，需和输入文件中的url字段保持一致。

Embedding文本向量模型填写/v1/embeddings

测试模型batch-test-model填写/v1/chat/ds-test

其他模型填写/v1/chat/completions

completion_window

String

Body

是

等待时间，支持最短等待时间24h，最长等待时间336h，仅支持整数。

支持"h"和"d"两个单位，如"24h"或"14d"。

metadata

Map

Body

否

任务扩展元数据，以键值对形式附加信息。

metadata.ds_name

String

Body

否

任务名称。

示例："ds_name"："Batch任务"

限制：长度不超过100个字符。

若重复定义该字段，以最后一次传入的值为准。

metadata.ds_description

String

Body

否

任务描述。

示例："ds_description"："Batch推理任务测试"

限制：长度不超过200个字符。

若重复定义该字段，以最后一次传入的值为准。

返回示例
 
{
    "id": "batch_xxx",
    "object": "batch",
    "endpoint": "/v1/chat/completions",
    "errors": null,
    "input_file_id": "file-batch-xxx",
    "completion_window": "24h",
    "status": "validating",
    "output_file_id": null,
    "error_file_id": null,
    "created_at": 1742367779,
    "in_progress_at": null,
    "expires_at": null,
    "finalizing_at": null,
    "completed_at": null,
    "failed_at": null,
    "expired_at": null,
    "cancelling_at": null,
    "cancelled_at": null,
    "request_counts": {
        "total": 0,
        "completed": 0,
        "failed": 0
    },
    "metadata": {
        "ds_name": "任务名称",
        "ds_description": "任务描述"
    }
}
返回参数



字段

类型

描述

id

String

Batch任务 ID。

object

String

对象类型，固定值batch。

endpoint

String

访问路径。

errors

Map

错误信息。

input_file_id

String

文件ID或OSS文件 URL或OSS文件资源标识符。

completion_window

String

等待时间，支持最短等待时间24h，最长等待时间336h，仅支持整数。

支持"h"和"d"两个单位，如"24h"或"14d"。

status

String

任务状态，包括validating、failed、in_progress、finalizing、completed、expired、cancelling、cancelled。

output_file_id

String

执行成功请求的输出文件id。

error_file_id

String

执行错误请求的输出文件id。

created_at

Integer

任务创建的Unix 时间戳（秒）。

in_progress_at

Integer

任务开始运行的Unix时间戳（秒）。

expires_at

Integer

任务开始超时的时间戳（秒）。

finalizing_at

Integer

任务最后开始时间戳（秒）。

completed_at

Integer

任务完成的时间戳（秒）。

failed_at

Integer

任务失败的时间戳（秒）。

expired_at

Integer

任务超时的时间戳（秒）。

cancelling_at

Integer

任务设置为取消中的时间戳（秒）。

cancelled_at

Integer

任务取消的时间戳（秒）。

request_counts

Map

不同状态的请求数量。

metadata

Map

附加信息，键值对。

metadata.ds_name

String

当前任务的任务名称。

metadata.ds_description

String

当前任务的任务描述。

3. 查询与管理Batch任务
查询Batch任务详情
通过传入创建Batch任务返回的Batch任务ID，来查询指定Batch任务的信息。当前仅支持查询30天之内创建的Batch任务。

接口限流：每个阿里云主账号每分钟1000次（由于Batch任务执行需要一些时间，建议创建Batch任务之后，每分钟调用1次该查询接口获取任务信息）。

OpenAI Python SDKcurl
请求示例
 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼服务的base_url
)
batch = client.batches.retrieve("batch_id")  # 将batch_id替换为Batch任务的id
print(batch)
输入参数配置





字段

类型

传参方式

必选

描述

batch_id

String

Path

是

需要查询的Batch任务的ID（创建Batch任务返回的Batch任务ID），以batch开头，例如“batch_xxx”。

返回示例
请参见创建Batch任务的返回示例。

返回参数
请参见创建Batch任务的返回参数。

返回参数中output_file_id和error_file_id可以通过下载Batch结果文件获取内容。

查询Batch任务列表
您可以使用 batches.list() 方法查询 Batch 任务列表，并通过分页机制逐步获取完整的任务列表。

使用 after 参数：传入上一页最后一个Batch任务的 ID，以获取下一页数据。

使用 limit 参数：设定返回的任务数量。

支持通过input_file_ids等参数进行过滤查询。

接口限流：每个阿里云主账号每分钟100次。

OpenAI Python SDKcurl
请求示例
 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼服务的base_url
)
batches = client.batches.list(after="batch_xxx", limit=2,extra_query={'ds_name':'任务名称','input_file_ids':'file-batch-xxx,file-batch-xxx','status':'completed,expired','create_after':'20250304000000','create_before':'20250306123000'})
print(batches)
输入参数配置





字段

类型

传参方式

必选

描述

after

String

Query

否

用于分页的游标，参数after的取值为Batch任务ID，表示查询该ID之后的数据。分页查询时，可以将返回结果中的最后一个Batch任务ID（last_id）赋值给该参数，以获取下一页的数据。

例如，若本次查询返回了20行数据，且最后一个Batch任务 ID（即last_id）是batch_xxx，则后续查询时可以设置after=batch_xxx，以获取列表的下一页。

limit

Integer

Query

否

每次查询返回的Batch任务数量，范围[1,100]，默认20。

ds_name

String

Query

否

根据任务名称进行模糊筛选，输入任意连续字符片段即可匹配包含该内容的任务名称（如输入“Batch”可匹配“ Batch任务”、“Batch任务_20240319”等）。

input_file_ids

String

Query

否

筛选多个文件ID，以英文逗号分隔，最多可填写20个。准备与上传文件返回的文件ID或OSS文件URL或资源标识符。

status

String

Query

否

筛选多个状态，以英文逗号分隔，包括validating、failed、in_progress、finalizing、completed、expired、cancelling、cancelled。

create_after

String

Query

否

筛选在此时间点之后创建的任务，格式：yyyyMMddHHmmss。例如，您想筛选2025年03月04日00点00分00秒时间点之后创建的任务，可写为20250304000000。

create_before

String

Query

否

筛选在此时间点之前创建的任务，格式：yyyyMMddHHmmss。例如，您想筛选2025年3月4日12点30分0秒时间点之前创建的任务，可写为20250304123000。

返回示例
 
{
  "object": "list",
  "data": [
    {
      "id": "batch_xxx",
      "object": "batch",
      "endpoint": "/v1/chat/completions",
      "errors": null,
      "input_file_id": "file-batch-xxx",
      "completion_window": "24h",
      "status": "completed",
      "output_file_id": "file-batch_output-xxx",
      "error_file_id": null,
      "created_at": 1722234109,
      "in_progress_at": 1722234109,
      "expires_at": null,
      "finalizing_at": 1722234165,
      "completed_at": 1722234165,
      "failed_at": null,
      "expired_at": null,
      "cancelling_at": null,
      "cancelled_at": null,
      "request_counts": {
        "total": 100,
        "completed": 95,
        "failed": 5
      },
      "metadata": {}
    },
    { ... }
  ],
  "first_id": "batch_xxx",
  "last_id": "batch_xxx",
  "has_more": true
}
返回参数



字段

类型

描述

object

String

类型，固定值list。

data

Array

Batch任务对象，参见创建Batch任务的返回参数。

first_id

String

当前页第一个 Batch任务 ID。

last_id

String

当前页最后一个Batch任务 ID。

has_more

Boolean

是否有下一页。

取消Batch任务
通过传入创建Batch任务返回的Batch任务ID，来取消指定的Batch任务。

接口限流：每个阿里云主账号每分钟1000次。

OpenAI Python SDKcurl
请求示例
 
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，可用阿里云百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼服务的base_url
)
batch = client.batches.cancel("batch_id")  # 将batch_id替换为Batch任务的id
print(batch)
输入参数配置





字段

类型

传参方式

必选

描述

batch_id

String

Path

是

需要取消的Batch任务的id，以batch开头，例如“batch_xxx”。

返回示例
请参见创建Batch任务的返回示例。

返回参数
请参见创建Batch任务的返回参数。

4. 下载Batch结果文件
在Batch推理任务结束后，您可以通过接口下载结果文件。

您可以通过查询Batch任务详情或通过查询Batch任务列表返回参数中的output_file_id获取下载文件的file_id。仅支持下载以file-batch_output开头的file_id对应的文件。
OpenAI Python SDKcurl
您可以通过content方法获取Batch任务结果文件内容，并通过write_to_file方法将其保存至本地。

请求示例
 
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
content = client.files.content(file_id="file-batch_output-xxx")
# 打印结果文件内容
print(content.text)
# 保存结果文件至本地
content.write_to_file("result.jsonl")
返回示例
 
{"id":"c308ef7f-xxx","custom_id":"1","response":{"status_code":200,"request_id":"c308ef7f-0824-9c46-96eb-73566f062426","body":{"created":1742303743,"usage":{"completion_tokens":35,"prompt_tokens":26,"total_tokens":61},"model":"qwen-plus","id":"chatcmpl-c308ef7f-0824-9c46-96eb-73566f062426","choices":[{"finish_reason":"stop","index":0,"message":{"content":"你好！当然可以。无论是需要信息查询、学习资料、解决问题的方法，还是其他任何帮助，我都在这里为你提供支持。请告诉我你需要什么方面的帮助？"}}],"object":"chat.completion"}},"error":null}
{"id":"73291560-xxx","custom_id":"2","response":{"status_code":200,"request_id":"73291560-7616-97bf-87f2-7d747bbe84fd","body":{"created":1742303743,"usage":{"completion_tokens":7,"prompt_tokens":26,"total_tokens":33},"model":"qwen-plus","id":"chatcmpl-73291560-7616-97bf-87f2-7d747bbe84fd","choices":[{"finish_reason":"stop","index":0,"message":{"content":"2+2 equals 4."}}],"object":"chat.completion"}},"error":null}
输入参数配置





字段

类型

传参方式

必选

描述

file_id

string

Path

是

需要下载的文件的ID，查询Batch任务详情或通过查询Batch任务列表返回参数中的output_file_id值。

返回结果
Batch任务结果的JSONL文件，格式请参考输出文件格式。

扩展功能
使用OSS文件创建Batch任务
创建Batch任务时，为避免上传文件的数量和总容量限制，您可通过input_file_id参数直接传入符合输入文件格式要求的OSS文件URL或资源标识符，无需调用接口上传文件。根据数据安全需求，可选择以下两种方式：

使用建议

数据安全要求

高安全性场景：优先采用方式二：使用OSS文件资源标识符，保障访问权限控制；

普通场景：可选择方式一：使用OSS文件URL，但存在链接泄露风险，您可进入目标bucket页面选择权限控制管理权限。

地域选择原则

建议您使用与阿里云百炼服务同地域cn-beijing的Bucket。

方式一：使用OSS文件URL
获取文件URL：

OSS管理控制台方式：

进入Bucket列表页面，找到目标Bucket并单击名称；

在文件列表中定位目标文件，单击右侧详情按钮；

您可在文件列表中新建子文件夹如Batch/20250317并上传文件，示例test.jsonl。
在弹出面板中，单击复制文件URL。

SDK方式：生成OSS文件URL，参考使用预签名URL下载文件。

参数配置：参数input_file_id填写OSS文件URL，示例：

 
input_file_id="https://testbucket.oss-cn-beijing.aliyuncs.com/xxx/xxx/Batch/20250317/test.jsonl?Expires=xxx"
方式二：使用OSS文件资源标识符
授权阿里云百炼访问当前账号下的OSS Bucket：

参阅OSS服务关联角色授权步骤完成授权并对目标Bucket添加标签。

参数配置：

参数input_file_id填写OSS文件的资源标识符，格式为oss:{region}:{bucket}/{file_path}，示例：

 
input_file_id="oss:cn-beijing:bucketTest/Batch/20250313/test.jsonl"
参数说明表：





字段

类型

必选

描述

region

String

是

OSS的bucket所在地域，如cn-beijing。

bucket

String

是

OSS的bucket名称，如bucketTest。

file_path

String

是

OSS文件路径，如Batch/20250313/test.jsonl。

Batch支持任务完成通知
Batch任务提交后可通过查询接口实时获取任务状态和执行信息，但频繁查询长时间运行的任务会导致效率低下，因此，Batch任务提供以下两种异步通知方式来获取任务完成的通知：

Callback回调：需要您提供一个公网可访问的API接口，任务完成后将自动推送状态到指定URL。适用于已有公网资源的场景，对接简单。

EventBridge消息队列：无需公网接口，但需要您自行创建RocketMQ消息队列来接收通知，适用于无公网服务的内部系统环境。

您可以根据具体需求和现有条件选择合适的通知方式，以提高任务管理的效率。

Callback回调
EventBridge消息队列
错误码
如果调用失败并返回报错信息，请参见错误信息进行解决。

常见问题
这几个模块的Batch定价，对应的模型也有基础限流吗？

答：实时调用才会有RPM（Requests Per Minute：每分钟处理请求数）限流，Batch调用没有 RPM 限流。

使用Batch调用，是否需要下单，在哪里下单？

答：Batch是一种调用方式，无需额外下单。该调用方式为后付费计价模式，按照Batch接口调用直接付费。

提交的Batch调用请求，后台如何处理？ 是根据提交请求的先后顺序来执行吗？

答：不是排队机制，是调度机制，根据资源情况来调度和执行Batch请求任务。

提交的Batch调用请求，实际执行完成需要多长时间？

答：Batch任务的执行时间取决于系统的资源分配情况。

在系统资源紧张时，任务可能无法在设定的最长等待时间内全部完成。

因此，对模型推理的时效性有严格要求的场景，建议使用实时调用；而对于处理大规模数据且对时效性有一定容忍度的场景，推荐使用Batch调用。
from openai import ChatCompletion
import openai

# Directly setting the OpenAI API key
OPENAI_API_KEY = "sk-8mPZt9WkHhWW-lAcwZ5c5powm21A38XoOWNQQVezd-T3BlbkFJ5xaGNSBiifV4vECACuvB2vHd66ZsCEkSVDKBzh6ukA"
openai.api_key = OPENAI_API_KEY

class AgentHead():
    def __init__(self, n_breakups):
        self.response_schema = []
        for i in range(0, n_breakups):
            self.response_schema.append(f"Sub-task number {i} of the given task")

    def generate_response(self, prompt):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a helpful assistant and will infer what needs to be done without asking any more questions."},
                          {"role": "user", "content": prompt}]
            )
            return response.choices[0].message['content']
        except Exception as e:
            print(f"Error in generating response: {e}")
            return None
        
    def breakup_task(self, task, focus_level):
        # define the focus level map
        focus_map = {
            "High": 3,
            "Medium": 5,
            "Low": 10
        }
        num_tasks = focus_map.get(focus_level, 10)

        # Call the GPT-3 API to break down the task
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant that specializes in breaking down tasks into smaller, manageable subtasks."
                    },
                    {
                        "role": "user",
                        "content": f"Break down the task: '{task}' into {num_tasks} subtasks. Each subtask must be strictly one sentence without punctuation or special characters"
                    }
                ]
            )
            # print (response['choices'][0]['message']['content'])
            # extract the breakdown from the response
            breakdown = response['choices'][0]['message']['content']
            # split the breakdown into subtasks
            subtasks = breakdown.strip().split("\n")
            # Ensure subtasks meet the one-sentence, no-punctuation rule
            subtasks = [subtask.strip() for subtask in subtasks]
            return subtasks[:num_tasks]  # return only the required number of subtasks
        except Exception as e:
            print(f"Error while calling GPT API: {e}")
            return []
            
        
    

# Example usage
if __name__ == "__main__":
    task_manager = AgentHead(5)
    task = "Organize a birthday party"
    focus_level = "low" # high, medium, low

    subtasks = task_manager.breakup_task(task, focus_level)
    print("Subtasks:", subtasks)

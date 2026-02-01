using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class LegoController : MonoBehaviour
{
    [Header("LEGO Object")]
    public GameObject legoPiece;
    
    [Header("Settings")]
    public string apiUrl = "http://localhost:5000/api/rotation";
    public bool smoothRotation = true;
    public float rotationSpeed = 5f;
    
    private Vector3 targetRotation = Vector3.zero;
    
    void Start()
    {
        if (legoPiece == null)
        {
            legoPiece = gameObject;
        }
        
        // Start polling for rotation updates from backend
        StartCoroutine(PollRotation());
    }
    
    void Update()
    {
        if (legoPiece != null && smoothRotation)
        {
            // Smoothly interpolate to target rotation
            legoPiece.transform.rotation = Quaternion.Lerp(
                legoPiece.transform.rotation,
                Quaternion.Euler(targetRotation),
                Time.deltaTime * rotationSpeed
            );
        }
    }
    
    // This method can be called from JavaScript
    public void SetRotation(string jsonData)
    {
        try
        {
            RotationData data = JsonUtility.FromJson<RotationData>(jsonData);
            targetRotation = new Vector3(data.x, data.y, data.z);
            
            if (!smoothRotation && legoPiece != null)
            {
                legoPiece.transform.rotation = Quaternion.Euler(targetRotation);
            }
            
            Debug.Log($"Rotation set to: X={data.x}, Y={data.y}, Z={data.z}");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Error parsing rotation data: {e.Message}");
        }
    }
    
    IEnumerator PollRotation()
    {
        while (true)
        {
            yield return new WaitForSeconds(0.1f); // Poll every 100ms
            
            using (UnityWebRequest request = UnityWebRequest.Get(apiUrl))
            {
                yield return request.SendWebRequest();
                
                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        RotationData data = JsonUtility.FromJson<RotationData>(request.downloadHandler.text);
                        targetRotation = new Vector3(data.x, data.y, data.z);
                    }
                    catch (System.Exception e)
                    {
                        Debug.LogError($"Error parsing rotation: {e.Message}");
                    }
                }
            }
        }
    }
}

[System.Serializable]
public class RotationData
{
    public float x;
    public float y;
    public float z;
}

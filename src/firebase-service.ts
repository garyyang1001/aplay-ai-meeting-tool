/**
 * Firebase 整合服務
 * 處理音頻檔案上傳、儲存和與 Mac Mini 的通信
 */

// Firebase 類型定義
interface FirebaseConfig {
    apiKey: string;
    authDomain: string;
    projectId: string;
    storageBucket: string;
    messagingSenderId: string;
    appId: string;
}

interface ProcessingJob {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    audioUrl?: string;
    transcript?: any[];
    analysis?: string;
    speakers?: any[];
    error?: string;
    createdAt: Date;
    updatedAt?: Date;
}

interface MacMiniStatus {
    available: boolean;
    url?: string;
    lastChecked: Date;
}

class FirebaseService {
    private app: any = null;
    private storage: any = null;
    private firestore: any = null;
    private config: FirebaseConfig | null = null;
    private macMiniStatus: MacMiniStatus = {
        available: false,
        lastChecked: new Date()
    };

    constructor() {
        this.loadConfig();
    }

    private loadConfig() {
        // 從環境變數或配置文件載入 Firebase 配置
        // 這裡使用環境變數，實際部署時需要設置
        this.config = {
            apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'your-api-key',
            authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'your-project.firebaseapp.com',
            projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'your-project-id',
            storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'your-project.appspot.com',
            messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '123456789',
            appId: import.meta.env.VITE_FIREBASE_APP_ID || 'your-app-id'
        };
    }

    /**
     * 初始化 Firebase
     */
    async initialize(): Promise<boolean> {
        try {
            // 動態載入 Firebase SDK
            const { initializeApp } = await import('firebase/app');
            const { getStorage } = await import('firebase/storage');
            const { getFirestore } = await import('firebase/firestore');

            if (!this.config) {
                console.warn('Firebase 配置不完整，使用本地模式');
                return false;
            }

            // 檢查配置是否為預設值
            if (this.config.apiKey === 'your-api-key') {
                console.warn('Firebase 配置為預設值，請更新 .env 文件');
                return false;
            }

            this.app = initializeApp(this.config);
            this.storage = getStorage(this.app);
            this.firestore = getFirestore(this.app);

            console.log('Firebase 初始化成功');
            return true;

        } catch (error) {
            console.error('Firebase 初始化失敗:', error);
            return false;
        }
    }

    /**
     * 上傳音頻檔案到 Firebase Storage
     */
    async uploadAudio(audioBlob: Blob, jobId: string): Promise<string | null> {
        if (!this.storage) {
            console.warn('Firebase Storage 未初始化，跳過上傳');
            return null;
        }

        try {
            const { ref, uploadBytes, getDownloadURL } = await import('firebase/storage');
            
            const fileName = `recordings/${jobId}-${Date.now()}.webm`;
            const storageRef = ref(this.storage, fileName);
            
            console.log(`上傳音頻檔案: ${fileName}`);
            
            const snapshot = await uploadBytes(storageRef, audioBlob);
            const downloadURL = await getDownloadURL(snapshot.ref);
            
            console.log('音頻上傳成功:', downloadURL);
            return downloadURL;

        } catch (error) {
            console.error('音頻上傳失敗:', error);
            return null;
        }
    }

    /**
     * 創建處理任務記錄
     */
    async createProcessingJob(jobData: Partial<ProcessingJob>): Promise<string | null> {
        if (!this.firestore) {
            console.warn('Firestore 未初始化，無法創建任務記錄');
            return null;
        }

        try {
            const { collection, addDoc } = await import('firebase/firestore');
            
            const jobsCollection = collection(this.firestore, 'processing_jobs');
            const jobDoc = await addDoc(jobsCollection, {
                ...jobData,
                createdAt: new Date(),
                status: 'pending'
            });

            console.log('處理任務創建成功:', jobDoc.id);
            return jobDoc.id;

        } catch (error) {
            console.error('創建處理任務失敗:', error);
            return null;
        }
    }

    /**
     * 檢查 Mac Mini 服務狀態
     */
    async checkMacMiniStatus(tunnelUrl?: string): Promise<MacMiniStatus> {
        const url = tunnelUrl || import.meta.env.VITE_MAC_MINI_URL;
        
        if (!url) {
            console.warn('Mac Mini URL 未設置');
            this.macMiniStatus = {
                available: false,
                lastChecked: new Date()
            };
            return this.macMiniStatus;
        }

        try {
            const response = await fetch(`${url}/health`, {
                method: 'GET',
                timeout: 5000,
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.macMiniStatus = {
                    available: true,
                    url: url,
                    lastChecked: new Date()
                };
                console.log('Mac Mini 服務可用:', data);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }

        } catch (error) {
            console.warn('Mac Mini 服務不可用:', error);
            this.macMiniStatus = {
                available: false,
                lastChecked: new Date()
            };
        }

        return this.macMiniStatus;
    }

    /**
     * 發送處理請求到 Mac Mini
     */
    async sendToMacMini(jobId: string, audioUrl: string, transcript?: any[]): Promise<boolean> {
        if (!this.macMiniStatus.available || !this.macMiniStatus.url) {
            console.warn('Mac Mini 服務不可用');
            return false;
        }

        try {
            const response = await fetch(`${this.macMiniStatus.url}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    job_id: jobId,
                    audio_url: audioUrl,
                    transcript: transcript,
                    analysis_type: '會議摘要'
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Mac Mini 處理請求發送成功:', result);
                return true;
            } else {
                throw new Error(`HTTP ${response.status}`);
            }

        } catch (error) {
            console.error('發送到 Mac Mini 失敗:', error);
            return false;
        }
    }

    /**
     * 輪詢處理結果
     */
    async pollForResult(jobId: string, maxAttempts: number = 60): Promise<ProcessingJob | null> {
        if (!this.firestore) {
            console.warn('Firestore 未初始化，無法輪詢結果');
            return null;
        }

        try {
            const { doc, getDoc } = await import('firebase/firestore');
            
            for (let attempt = 0; attempt < maxAttempts; attempt++) {
                await new Promise(resolve => setTimeout(resolve, 5000)); // 等待 5 秒
                
                const jobDoc = doc(this.firestore, 'processing_jobs', jobId);
                const jobSnapshot = await getDoc(jobDoc);
                
                if (jobSnapshot.exists()) {
                    const jobData = jobSnapshot.data() as ProcessingJob;
                    
                    if (jobData.status === 'completed' || jobData.status === 'failed') {
                        console.log('處理完成:', jobData);
                        return jobData;
                    }
                }
                
                console.log(`輪詢中... (${attempt + 1}/${maxAttempts})`);
            }
            
            console.warn('輪詢超時');
            return null;

        } catch (error) {
            console.error('輪詢結果失敗:', error);
            return null;
        }
    }

    /**
     * 獲取 Mac Mini 狀態
     */
    getMacMiniStatus(): MacMiniStatus {
        return this.macMiniStatus;
    }

    /**
     * 檢查 Firebase 是否可用
     */
    isAvailable(): boolean {
        return this.app !== null && this.storage !== null && this.firestore !== null;
    }

    /**
     * 創建本地備份（當 Firebase 不可用時）
     */
    createLocalBackup(jobId: string, data: any): void {
        try {
            const backupData = {
                jobId,
                data,
                timestamp: new Date().toISOString()
            };
            
            localStorage.setItem(`backup_${jobId}`, JSON.stringify(backupData));
            console.log('本地備份創建成功');

        } catch (error) {
            console.error('本地備份失敗:', error);
        }
    }

    /**
     * 獲取本地備份
     */
    getLocalBackup(jobId: string): any | null {
        try {
            const backup = localStorage.getItem(`backup_${jobId}`);
            return backup ? JSON.parse(backup) : null;

        } catch (error) {
            console.error('獲取本地備份失敗:', error);
            return null;
        }
    }

    /**
     * 清理本地備份
     */
    cleanupLocalBackups(): void {
        try {
            const keys = Object.keys(localStorage);
            keys.forEach(key => {
                if (key.startsWith('backup_')) {
                    localStorage.removeItem(key);
                }
            });
            console.log('本地備份清理完成');

        } catch (error) {
            console.error('清理本地備份失敗:', error);
        }
    }
}

// 導出單例
export const firebaseService = new FirebaseService();
export default firebaseService;

# 프론트엔드 아키텍처

## 1. 디렉토리 구조

```mermaid
graph TD
    subgraph frontend/src
        A[index.js] --> B[App.js]
        B --> C[pages/MainPage.js]
        B --> D[pages/ErrorPage.js]

        C --> E[hooks/useAnalyze.js]
        C --> F[Api.js]

        subgraph components
            G[default/]
            H[input/]
            I[result/]
            J[ui/]
        end

        C --> G
        C --> H
        C --> I
        C --> J

        G --> G1[PageHeader.jsx]
        G --> G2[Footer.jsx]
        G --> G3[ServiceIntroModal.jsx]

        H --> H1[InputModeSelector.jsx]
        H --> H2[TextInput.jsx]
        H --> H3[ImageUploader.jsx]
        H --> H4[PdfUploader.jsx]

        I --> I1[ResultDisplay.jsx]
        I --> I2[LoadingSpinner.jsx]
        I --> I3[SecondLoadingSpinner.jsx]
        I --> I4[FeedbackLoopSelector.jsx]
        I --> I5[ServiceReference.jsx]

        J --> J1[GhostButton.jsx]
    end
```

---

## 2. 상태 흐름 (State Flow)

```mermaid
stateDiagram-v2
    [*] --> input

    input: 입력 화면
    loading: 1차 분석 중
    completed: 결과 표시
    retryLoading: 2차 질의 중

    input --> loading: 제출
    loading --> completed: 분석 완료
    loading --> input: 에러/재시도

    completed --> retryLoading: 불만족 (2차 질의)
    completed --> [*]: 만족 + 종료

    retryLoading --> completed: 2차 분석 완료
    retryLoading --> completed: 에러

    completed --> input: 다른 질문하기
```

---

## 3. 컴포넌트 계층 구조

```mermaid
graph TB
    App[App.js]
    App --> |에러 시| ErrorPage
    App --> |정상| MainPage

    subgraph MainPage.js
        direction TB
        MP[MainPage]

        MP --> PageHeader
        MP --> VS{viewState}
        MP --> Footer

        VS --> |input| InputView
        VS --> |loading| LoadingView
        VS --> |completed| CompletedView

        subgraph InputView[입력 화면]
            GuideSection
            InputModeSelector
            TextInput
            ImageUploader
        end

        subgraph LoadingView[로딩 화면]
            UserQuerySummary
            LoadingSpinner
        end

        subgraph CompletedView[결과 화면]
            ResultDisplay1[ResultDisplay - 1차]
            SecondLoadingSpinner
            ResultDisplay2[ResultDisplay - 2차]
            FeedbackLoopSelector
            ServiceReference
            AskOtherWorkSelector
        end
    end
```

---

## 4. 데이터 흐름 (SSE 통신)

```mermaid
sequenceDiagram
    participant U as 사용자
    participant M as MainPage
    participant H as useAnalyze Hook
    participant B as Backend API

    U->>M: 파일/텍스트 입력 후 제출
    M->>H: fetchAnalyze(file)
    H->>B: POST /api/v1/analyze (SSE)

    loop SSE 스트림
        B-->>H: event: progress (phase)
        H-->>M: setPhase(relevance/search/...)
        M-->>U: 로딩 UI 업데이트
    end

    B-->>H: event: completed
    H-->>M: setFirstResponse(data)
    M-->>U: 1차 결과 표시

    U->>M: 불만족 클릭
    M->>H: fetchRetry(adminSummary)
    H->>B: POST /api/v1/retry (SSE)

    loop SSE 스트림
        B-->>H: event: progress
        H-->>M: setPhase(...)
    end

    B-->>H: event: completed
    H-->>M: setSecondResponse(data)
    M-->>U: 2차 결과 표시
```

---

## 5. SSE Phase 진행 상태

```mermaid
graph LR
    subgraph SSE 분석 단계
        P1[relevance] --> P2[search]
        P2 --> P3[summarize]
        P3 --> P4[translate]
        P4 --> P5[validate]
        P5 --> P6[completed]
    end

    P1 -.-> E1[close]
    P2 -.-> E2[failed]
    P3 -.-> E3[error]

    style P6 fill:#4CAF50,color:#fff
    style E1 fill:#f44336,color:#fff
    style E2 fill:#f44336,color:#fff
    style E3 fill:#f44336,color:#fff
```

---

## 6. 기술 스택 다이어그램

```mermaid
graph TB
    subgraph Frontend Stack
        R[React 19]
        R --> CRA[Create React App]

        subgraph UI Layer
            MUI[MUI 7.x]
            TW[Tailwind CSS 3.x]
            EM[Emotion]
        end

        subgraph Data Layer
            SS[SessionStorage]
            IDB[IndexedDB]
            SSE[SSE Streaming]
        end

        subgraph Utilities
            RM[react-markdown]
            IK[idb-keyval]
        end

        R --> MUI
        R --> TW
        MUI --> EM
        R --> SS
        R --> IDB
        R --> SSE
        R --> RM
        IDB --> IK
    end
```

---

## 7. 사용자 여정 (User Flow)

```mermaid
flowchart TD
    Start([시작]) --> Input[입력 화면]
    Input --> SelectMode{입력 방식 선택}

    SelectMode --> |텍스트| TextInput[텍스트 입력]
    SelectMode --> |이미지| ImageUpload[이미지 업로드]
    SelectMode --> |PDF| PdfUpload[PDF 업로드]

    TextInput --> Submit[제출]
    ImageUpload --> Submit
    PdfUpload --> Submit

    Submit --> Loading[1차 분석 중<br/>SSE 진행상황 표시]
    Loading --> |완료| Result1[1차 결과 표시]
    Loading --> |에러| ErrorHandle{에러 처리}

    ErrorHandle --> |재시도| Submit
    ErrorHandle --> |심각한 에러| ErrorPage[에러 페이지]

    Result1 --> Feedback{만족하시나요?}

    Feedback --> |예| ShowRef[참고자료 표시]
    Feedback --> |아니오| Retry[2차 질의]

    Retry --> Loading2[2차 분석 중]
    Loading2 --> Result2[2차 결과 표시]
    Result2 --> ShowRef

    ShowRef --> Final{다음 행동}
    Final --> |다른 질문| Input
    Final --> |복지센터 이동| External([외부 링크])
    Final --> |종료| End([종료])
```

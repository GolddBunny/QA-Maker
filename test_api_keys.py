#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 키 연결 테스트 스크립트
GPT, Anthropic, Cohere API 키가 정상적으로 작동하는지 확인합니다.
"""

import os
import asyncio
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def test_openai_api():
    """OpenAI GPT API 테스트"""
    try:
        import openai
        
        api_key = os.getenv('capston_GPT_API_KEY') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            return False, "GPT_API_KEY 또는 OPENAI_API_KEY 환경변수가 설정되지 않았습니다."
        
        client = openai.OpenAI(api_key=api_key)
        
        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": """카톡 답장 수정해줘. 민승님 안녕하세요!!
좋은 기회 알려주셔서 정말 감사합니다!
제가 최근에 회사에서 중요한 제품 개발 프로젝트의 메인 PM을 맡게 되었습니다..ㅎㅎ 정말 좋은 기회라서 고민을 많이 해봤는데, 지금 이 시점에서 나가게 되면 회사와 팀에 너무 곤란한 상황이 될 것 같더라고요
이번 프로젝트가 저에게도 정말 중요한 경험이 될 것 같아서, 아무래도 여기서 결과를 한번 보고 싶습니다!"""}],
            max_tokens=1000
        )
        
        return True, f"✅ OpenAI API 연결 성공! 응답: {response.choices[0].message.content.strip()}"
        
    except ImportError:
        return False, "❌ openai 패키지가 설치되지 않았습니다. 'pip install openai' 실행 필요"
    except Exception as e:
        return False, f"❌ OpenAI API 오류: {str(e)}"

def test_anthropic_api():
    """Anthropic Claude API 테스트"""
    try:
        import anthropic
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return False, "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다."
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # 간단한 테스트 요청
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        return True, f"✅ Anthropic API 연결 성공! 응답: {response.content[0].text.strip()}"
        
    except ImportError:
        return False, "❌ anthropic 패키지가 설치되지 않았습니다. 'pip install anthropic' 실행 필요"
    except Exception as e:
        return False, f"❌ Anthropic API 오류: {str(e)}"

def test_cohere_api():
    """Cohere API 테스트"""
    try:
        import cohere
        
        api_key = os.getenv('COHERE_API_KEY')
        if not api_key:
            return False, "COHERE_API_KEY 환경변수가 설정되지 않았습니다."
        
        client = cohere.Client(api_key)
        
        # 간단한 테스트 요청
        response = client.generate(
            model='command-r-plus',
            prompt='Hello',
            max_tokens=10
        )
        
        return True, f"✅ Cohere API 연결 성공! 응답: {response.generations[0].text.strip()}"
        
    except ImportError:
        return False, "❌ cohere 패키지가 설치되지 않았습니다. 'pip install cohere' 실행 필요"
    except Exception as e:
        return False, f"❌ Cohere API 오류: {str(e)}"

def main():
    """메인 테스트 함수"""
    print("🔍 API 키 연결 테스트를 시작합니다...\n")
    
    # 환경변수 확인
    print("📋 환경변수 확인:")
    gpt_key = os.getenv('capston_GPT_API_KEY') or os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    cohere_key = os.getenv('COHERE_API_KEY')
    
    print(f"   GPT_API_KEY: {'✅ 설정됨' if gpt_key else '❌ 미설정'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ 설정됨' if anthropic_key else '❌ 미설정'}")
    print(f"   COHERE_API_KEY: {'✅ 설정됨' if cohere_key else '❌ 미설정'}")
    print()
    
    # GPT API 100번 반복 테스트
    print("🚀 OpenAI GPT API 100번 반복 테스트를 시작합니다...")
    print("=" * 60)
    
    gpt_success_count = 0
    gpt_fail_count = 0
    error_messages = []
    
    for i in range(1, 10):
        print(f"테스트 {i}/100 진행 중...", end=" ")
        success, message = test_openai_api()
        
        if success:
            gpt_success_count += 1
            print("✅")
        else:
            gpt_fail_count += 1
            print("❌")
            error_messages.append(f"테스트 {i}: {message}")
    
    print("\n" + "=" * 60)
    print("📊 GPT API 100회 테스트 결과:")
    print(f"   ✅ 성공: {gpt_success_count}회")
    print(f"   ❌ 실패: {gpt_fail_count}회")
    print(f"   📈 성공률: {gpt_success_count}%")
    
    if error_messages:
        print(f"\n❌ 실패한 테스트들:")
        for error in error_messages[:5]:  # 처음 5개만 표시
            print(f"   {error}")
        if len(error_messages) > 5:
            print(f"   ... 총 {len(error_messages)}개의 실패")
    
    print("\n" + "=" * 60)
    
    # 다른 API들은 1번씩만 테스트
    print("🧪 다른 API들 테스트 중...")
    other_tests = [
        ("Anthropic Claude", test_anthropic_api),
        ("Cohere", test_cohere_api)
    ]
    
    other_results = []
    
    for name, test_func in other_tests:
        print(f"🔍 {name} API 테스트 중...")
        success, message = test_func()
        other_results.append((name, success, message))
        print(f"   {message}")
        print()
    
    # 최종 결과 요약
    print("=" * 60)
    print("🎯 최종 테스트 결과:")
    print(f"   OpenAI GPT: {gpt_success_count}/100 성공 ({gpt_success_count}%)")
    
    for name, success, _ in other_results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {name}: {status}")
    
    if gpt_success_count >= 95:
        print("\n🎉 GPT API가 매우 안정적으로 작동합니다!")
    elif gpt_success_count >= 80:
        print("\n⚠️  GPT API가 대체로 안정적이지만 간헐적 오류가 있습니다.")
    else:
        print("\n❌ GPT API에 심각한 문제가 있습니다. API 키나 네트워크를 확인해주세요.")

if __name__ == "__main__":
    main() 